from odoo import models, _
from odoo.exceptions import UserError


class L10nClRcvSiiService(models.AbstractModel):
    _name = "l10n_cl.rcv.sii.service"
    _description = "Servicio SII RCV Chile"

    # Método llamado por el wizard
    def fetch_rcv(self, company, year, month, import_type):
        """
        Punto de entrada desde el wizard.
        """
        return self.import_rcv(company, year, month, import_type)

    # Implementación base del servicio
    def import_rcv(self, company, year, month, import_type):
        """
        Servicio base SII (etapa 3B.2).
        El login real y consumo SII se implementan en 3B.3+.
        """

        if not company:
            raise UserError(_("Empresa no definida para importar RCV."))

        if not year or not month:
            raise UserError(_("Debe indicar año y mes para importar el RCV."))

        # Etapa actual: servicio base validado
        # Aquí irá:
        # - Login SII real
        # - Mutual TLS
        # - Cookies
        # - Descarga RCV compras/ventas

        raise UserError(
            _(
                "Servicio SII base activo.\n\n"
                "El flujo está correcto, pero la conexión real al SII\n"
                "se implementa en el PASO 3B.3."
            )
        )
