from odoo import models, _
from odoo.exceptions import UserError


class L10nClRcvSiiService(models.AbstractModel):
    _name = "l10n_cl.rcv.sii.service"
    _description = "Servicio SII RCV Chile (Base)"

    def import_rcv(self, company, year, month, import_type):
        """
        Servicio base SII.
        En esta etapa solo valida que el flujo funcione.
        El login real SII se implementa en 3B.3+
        """

        # Validación defensiva
        if not company:
            raise UserError(_("Empresa no definida para importar RCV."))

        # ⚠️ Etapa actual: servicio base
        # Aquí luego irá:
        # - Login SII
        # - Mutual TLS
        # - Cookies
        # - Descarga real RCV

        raise UserError(
            _(
                "Servicio SII base activo.\n\n"
                "La conexión real al SII se implementa en el PASO 3B.3."
            )
        )