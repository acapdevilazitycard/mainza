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

    def _get_quantity_from_move_for_picking(self, move, sign):

        #return move.quantity * sign
        return move.product_uom_qty * sign

    def _process_section_note_lines_grouped(
            self, previous_section, previous_note, target_dict, group_key
    ):
        """
        Procesa secciones y notas, añadiéndolas a un diccionario target_dict bajo una group_key.
        group_key puede ser un picking_id, un sale_order_id.
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

        picking_lines_data = {}
        sale_order_lines_data = {}
        other_lines_data = {} #nuevo

        no_picking_placeholder = self.env["stock.picking"].browse([])
        no_so_placeholder = self.env["sale.order"].browse([])
        sign = -1.0 if self.move_type == 'out_refund' else 1.0

        so_to_picking_map = {p.sale_id: p for p in self.picking_ids if p.sale_id}

        previous_section = previous_note = False
        sorted_invoice_lines = self.invoice_line_ids.sorted('sequence')

        for inv_line in sorted_invoice_lines:
            if inv_line.display_type in ("line_section", "line_note"):
                if inv_line.display_type == "line_section":
                    previous_section = inv_line
                    previous_note = False
                else:
                    previous_note = inv_line
                continue

            notes_processed_for_line = False

            # PASO 1: CALCULAR Y AGRUPAR LA PARTE ENTREGADA ('DONE')
            # Agrupamos los movimientos por su albarán 'done' para sumar correctamente.
            done_pickings_moves = {}
            if inv_line.move_line_ids:
                for move in inv_line.move_line_ids:
                    if move.picking_id and move.picking_id.state == 'done':
                        if move.picking_id not in done_pickings_moves:
                            done_pickings_moves[move.picking_id] = []
                        done_pickings_moves[move.picking_id].append(move)

            total_delivered_qty_signed = 0.0
            if done_pickings_moves:
                for picking_record, moves_list in done_pickings_moves.items():
                    # Si hay notas/secciones pendientes, se asocian al primer grupo que se crea.
                    if not notes_processed_for_line:
                        self._process_section_note_lines_grouped(
                            previous_section, previous_note, picking_lines_data, picking_record
                        )
                        notes_processed_for_line = True

                    key = (picking_record, inv_line)
                    qty_for_this_picking = 0.0
                    for move in moves_list:
                        qty_for_this_picking += self._get_quantity_from_move_for_picking(move, sign)
                    picking_lines_data[key] = qty_for_this_picking
                    total_delivered_qty_signed += qty_for_this_picking

            # PASO 2: CALCULAR Y AGRUPAR LA PARTE PENDIENTE
            signed_invoice_qty = inv_line.quantity * sign

            # Usamos is_zero para evitar problemas de precisión con floats
            pending_qty_signed = signed_invoice_qty - total_delivered_qty_signed

            if not inv_line.currency_id.is_zero(pending_qty_signed):
                # Hay una cantidad pendiente, la agrupamos por Pedido de Venta.
                current_sale_order = inv_line.sale_line_ids[0].order_id if inv_line.sale_line_ids else None
                if current_sale_order:
                    # Si las notas no se asociaron antes, se asocian ahora.
                    if not notes_processed_for_line:
                        self._process_section_note_lines_grouped(
                            previous_section, previous_note, sale_order_lines_data, current_sale_order
                        )
                        notes_processed_for_line = True

                    key = (current_sale_order, inv_line)
                    sale_order_lines_data[key] = pending_qty_signed
                else:
                    if not notes_processed_for_line:

                        self._process_section_note_lines_grouped(
                            previous_section, previous_note, other_lines_data, inv_line
                        )
                        notes_processed_for_line = True
                    other_lines_data[(inv_line, inv_line)] = pending_qty_signed

            # Limpiamos las notas/secciones si fueron procesadas para esta línea.
            if notes_processed_for_line:
                previous_section = previous_note = False

        # --- Construcción de la lista final (sin cambios) ---
        final_report_lines = []
        # Grupo "Entregado"
        for (picking, aml), qty in picking_lines_data.items():
            final_report_lines.append({
                "group_by": "picking", "picking": picking,
                "sale_order": picking.sale_id or no_so_placeholder,
                "line": aml, "quantity": qty,
            })
        # Grupo "No Entregado"
        for (so, aml), qty in sale_order_lines_data.items():
            final_report_lines.append({
                "group_by": "sale_order", "picking": so_to_picking_map.get(so, no_picking_placeholder),
                "sale_order": so, "line": aml, "quantity": qty,
            })

        for (group_key, aml), qty in other_lines_data.items():
            line_to_add = aml if aml.display_type not in ('line_section', 'line_note') else group_key

            final_report_lines.append({
                "group_by": "other",  # Grupo "Other"
                "picking": no_picking_placeholder,
                "sale_order": no_so_placeholder,
                "line": line_to_add,
                "quantity": qty,
            })

        return self._sort_grouped_lines_final(final_report_lines)

    @api.model_create_multi
    def create(self, vals_list):
        moves = super().create(vals_list)
        for move in moves:
            if move.ref and move.ref.startswith(', '):
                new_ref = move.ref[2:]
                move.write({'ref': new_ref})

        return moves