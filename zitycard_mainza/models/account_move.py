from datetime import datetime

from odoo import api, models

class AccountMove(models.Model):
    _inherit = "account.move"

    @api.model
    def _sort_grouped_lines_final(self, lines_list):  # Renombrado para evitar conflictos
        DTF = "%Y-%m-%d %H:%M:%S"
        min_date_dt = datetime.min
        min_date_str = min_date_dt.strftime(DTF)

        return sorted(
            lines_list,
            key=lambda x: (
                # Prioridad de Grupo:  Sale Order > Picking  > Other
                0 if x.get("group_by") == "sale_order" else 1 if x.get("group_by") == "picking" else 2,

                # Orden para grupo "picking"
                (x["picking"].date or min_date_dt).strftime(DTF)
                if x.get("group_by") == "picking" and x.get("picking") else min_date_str,
                (x["picking"].date_done or x["picking"].date or min_date_dt).strftime(DTF)
                if x.get("group_by") == "picking" and x.get("picking") else min_date_str,
                x["picking"].name if x.get("group_by") == "picking" and x.get("picking") else "",

                # Orden para grupo "sale_order"
                (x["sale_order"].date_order or min_date_dt).strftime(DTF)
                if x.get("group_by") == "sale_order" and x.get("sale_order") else min_date_str,
                x["sale_order"].name if x.get("group_by") == "sale_order" and x.get("sale_order") else "",

                # Notas al final dentro de su (sub)grupo
                x.get("is_last_section_notes", False),
                # Orden de líneas dentro del grupo
                x["line"].sequence if x["line"] else 0,
                x["line"].id if x["line"] else 0,
            ),
        )

    def _get_signed_quantity_done(self, invoice_line, move, sign):  # 'move' es un stock.move
        """
        Hook method. 'move' es un 'stock.move' record.
        Calcula la cantidad 'hecha' sumando de las stock.move.line asociadas.
        """
        qty_actually_done = 0.0
        # 'move.move_line_ids' es la relación One2many de stock.move a stock.move.line
        for sml in move.move_line_ids.filtered(lambda l: l.state == 'done'):
            sml_qty_done_field_name = 'quantity_done' if hasattr(sml, 'quantity_done') else 'qty_done'

            current_sml_qty = getattr(sml, sml_qty_done_field_name, 0.0)

            if sml.location_id.usage == "customer":  # Retorno a la empresa desde el cliente
                qty_actually_done -= current_sml_qty
            elif sml.location_dest_id.usage == "customer":  # Entrega al cliente
                qty_actually_done += current_sml_qty

        return qty_actually_done * sign

    def _process_section_note_lines_grouped(
            self, previous_section, previous_note, target_dict, group_key
    ):
        """
        Procesa secciones y notas, añadiéndolas a un diccionario target_dict bajo una group_key.
        group_key puede ser un picking_id, un sale_order_id, o un placeholder para "otros".
        target_dict será (group_key, account_move_line_section_or_note) -> 0.0
        """
        for line_obj in [previous_section, previous_note]:
            if line_obj:
                key_for_section_note = (group_key, line_obj)
                target_dict.setdefault(key_for_section_note, 0.0)  # La cantidad es 0 para secciones/notas

    def _get_grouped_by_picking_sorted_lines(self):
        """Sorts the invoicelines to be grouped by picking."""
        return self.invoice_line_ids.sorted(
            lambda ln: (-ln.sequence, ln.date, str(ln.move_name or ''), -ln.id), reverse=True
        )

    def lines_grouped_by_picking(self):
        self.ensure_one()


        picking_lines_data = {}  # Para líneas agrupadas por picking
        sale_order_lines_data = {}  # Para líneas (sin picking) agrupadas por SO
        other_lines_data = {}  # Para líneas sin picking ni SO

        no_picking_placeholder = self.env["stock.picking"].browse([])  # Para el picking en la estructura final
        no_so_placeholder = self.env["sale.order"].browse([])  # Para el SO en la estructura final

        sign = (
            -1.0
            if self.move_type == "out_refund"
               and (
                       not self.reversed_entry_id
                       or self.reversed_entry_id.picking_ids != self.picking_ids
               )
            else 1.0
        )

        so_to_picking_map = {p.sale_id: p for p in self.picking_ids if p.sale_id}

        previous_section = previous_note = False

        sorted_invoice_lines = self._get_grouped_by_picking_sorted_lines()

        for inv_line in sorted_invoice_lines:
            if inv_line.display_type in ["line_section", "line_note"]:
                if inv_line.display_type == "line_section":
                    if previous_section:
                        pass
                    previous_section = inv_line
                    previous_note = False  # Nueva sección limpia nota anterior
                else:  # es line_note
                    if previous_note:
                        # Similar a la sección, si hay nota-nota sin producto intermedio.
                        pass
                    previous_note = inv_line
                continue  # Continuar para que se asocien con la siguiente línea de producto

            # --- Inicio de la lógica de asignación de grupo para la línea de producto ---
            associated_to_picking_group = False
            if inv_line.move_line_ids:  # En Odoo 17, move_line_ids en account.move.line es M2M a stock.move
                for move in inv_line.move_line_ids:  # move es un stock.move
                    if move.picking_id:
                        current_picking = move.picking_id
                        # Procesar secciones/notas pendientes para este grupo de picking
                        self._process_section_note_lines_grouped(previous_section, previous_note,
                                                                 picking_lines_data, current_picking)

                        key = (current_picking, inv_line)
                        # Usamos la función _get_signed_quantity_done original que espera un stock.move
                        qty = self._get_signed_quantity_done(inv_line, move, sign)
                        picking_lines_data[key] = picking_lines_data.get(key, 0.0) + qty

                        if move.location_id.usage == "customer":  # Del original
                            has_returned_qty = True
                        associated_to_picking_group = True
                    # else: el move no tiene picking_id, se ignora para el grupo de picking.
                    # Podría considerarse para SO si el move tiene SO y no picking.

            if not associated_to_picking_group:
                if inv_line.sale_line_ids:
                    # Asumir que todas las sale_line_ids de una inv_line son del mismo order_id,
                    # o tomar el primero como representativo.
                    current_sale_order = inv_line.sale_line_ids[0].order_id
                    if current_sale_order:
                        # Procesar secciones/notas pendientes para este grupo de SO
                        self._process_section_note_lines_grouped(previous_section, previous_note,
                                                                 sale_order_lines_data, current_sale_order)

                        key = (current_sale_order, inv_line)
                        # La cantidad es la total de la línea de factura, ya que no se asoció a picking.
                        qty = inv_line.quantity * sign
                        sale_order_lines_data[key] = sale_order_lines_data.get(key, 0.0) + qty
                    else:  # sale_line_ids pero sin order_id (raro) -> va a "Otros"
                        self._process_section_note_lines_grouped(previous_section, previous_note, other_lines_data,
                                                                 None)  # None como clave para "Otros"
                        key = (None, inv_line)
                        other_lines_data[key] = other_lines_data.get(key, 0.0) + (inv_line.quantity * sign)
                else:  # Sin picking y sin SO -> va a "Otros"
                    self._process_section_note_lines_grouped(previous_section, previous_note, other_lines_data,
                                                             None)
                    key = (None, inv_line)  # (None representa el grupo "Otros", inv_line es la línea de producto)
                    other_lines_data[key] = other_lines_data.get(key, 0.0) + (inv_line.quantity * sign)

            # Limpiar secciones/notas pendientes ya que se han asociado a un grupo de producto.
            previous_section = previous_note = False

        # Estructurar la lista final para el reporte
        final_report_lines = []

        # Líneas de Picking
        for (picking_record, aml), qty in picking_lines_data.items():
            # Si aml es una sección/nota, qty es 0.0 (seteado por _process_section_note_lines_grouped)
            # Si aml es producto, qty es la calculada.
            final_report_lines.append({
                "group_by": "picking",
                "picking": picking_record,
                "sale_order": picking_record.sale_id if picking_record else no_so_placeholder,
                # SO del picking si existe
                "line": aml,
                "quantity": qty,
                "is_last_section_notes": False,  # Secciones/notas aquí no son "trailing" globales
            })

        # Líneas de Sale Order (sin picking)
        for (so_record, aml), qty in sale_order_lines_data.items():
            final_report_lines.append({
                "group_by": "sale_order",
                "picking": so_to_picking_map.get(so_record, no_picking_placeholder),
                # Intenta encontrar un picking asociado
                "sale_order": so_record,
                "line": aml,
                "quantity": qty,
                "is_last_section_notes": False,
            })

        # Líneas "Otros"
        for (group_key_none, aml), qty in other_lines_data.items():  # group_key_none es None
            final_report_lines.append({
                "group_by": "other",
                "picking": no_picking_placeholder,
                "sale_order": no_so_placeholder,
                "line": aml,
                "quantity": qty,
                "is_last_section_notes": False,
            })

        if previous_section:
            final_report_lines.append({
                "group_by": "other", "picking": no_picking_placeholder, "sale_order": no_so_placeholder,
                "line": previous_section, "quantity": 0.0, "is_last_section_notes": True,
            })
        if previous_note:
            final_report_lines.append({
                "group_by": "other", "picking": no_picking_placeholder, "sale_order": no_so_placeholder,
                "line": previous_note, "quantity": 0.0, "is_last_section_notes": True,
            })

        sorted_list = self._sort_grouped_lines_final(final_report_lines)
        return sorted_list