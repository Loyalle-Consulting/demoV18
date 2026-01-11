# -*- coding: utf-8 -*-
from odoo import models

class StockPicking(models.Model):
    _inherit = "stock.picking"

    def _prepare_pdf_values(self):
        """
        Fuerza a que el reporte valore usando el precio del MOVIMIENTO (stock.move.price_unit)
        o, si tienes un campo manual distinto, úsalo en preferencia.
        Recalcula total_line_amounts y amounts para que QWeb muestre totales correctos.
        """
        res = super()._prepare_pdf_values()
        try:
            # Diccionarios que consume el QWeb de la guía chilena
            total_line_amounts = dict(res.get("total_line_amounts", {}))  # { move: {...} }
            amounts = dict(res.get("amounts", {}))                        # totales

            # IVA por defecto si no viene desde la base
            vat_percent = float(amounts.get("vat_percent", 19) or 19.0)

            # Filtramos las líneas visibles (sin paquete) tal como hace la vista
            self.ensure_one()
            moves = self.move_ids_without_package.filtered(lambda m: (m.quantity or m.product_uom_qty))

            sum_taxable = 0.0
            sum_exempt = float(amounts.get("subtotal_amount_exempt", 0.0) or 0.0)
            has_discount = bool(res.get("has_discount", False))

            for m in moves:
                # Cantidad entregada o solicitada
                qty = float((m.quantity or 0.0) if (m.quantity or 0.0) else (m.product_uom_qty or 0.0))

                # Precio del movimiento (prioriza tu campo manual si lo tuvieras)
                unit = (
                    getattr(m, "x_unit_price_manual", False)
                    or getattr(m, "x_price_unit_manual", False)
                    or getattr(m, "x_price_unit", False)
                    or getattr(m, "x_unit_price", False)
                    or m.price_unit
                    or 0.0
                )
                unit = float(unit or 0.0)

                # Descuento por línea si lo usas (ajusta el nombre si es otro)
                disc = float(getattr(m, "x_discount_amount", 0.0) or 0.0)
                if disc:
                    has_discount = True

                line_subtotal = max(unit * qty - disc, 0.0)

                # Actualiza la estructura por línea que ya lee el QWeb
                base_vals = total_line_amounts.get(m, {})
                base_vals.update({
                    "price_unit": unit,
                    "total_discount_fl": disc,
                    "total_amount": line_subtotal,
                })
                total_line_amounts[m] = base_vals

                # Si manejas exento por línea, separa aquí. Por defecto lo consideramos afecto.
                # if getattr(m, "is_exempt", False):
                #     sum_exempt += line_subtotal
                # else:
                sum_taxable += line_subtotal

            vat_amount = sum_taxable * vat_percent / 100.0
            total_amount = sum_taxable + sum_exempt + vat_amount

            amounts.update({
                "subtotal_amount_taxable": sum_taxable,
                "subtotal_amount_exempt": sum_exempt,
                "vat_percent": vat_percent,
                "vat_amount": vat_amount,
                "total_amount": total_amount,
            })

            res.update({
                "has_unit_price": True,
                "has_discount": has_discount,
                "amounts": amounts,
                "total_line_amounts": total_line_amounts,
            })
            return res
        except Exception:
            # Si algo no cuadra, no rompemos el render
            return res