/** @odoo-module **/

import { DocumentsControlPanel } from "@documents/views/search/documents_control_panel";
import { patch } from "@web/core/utils/patch";
import { useState } from "@odoo/owl";

patch(DocumentsControlPanel.prototype, {
    setup() {
        super.setup();
        this.restrictionFlags = useState({
            export: true,
            archive: true,
            unarchive: true,
            duplicate: true,
        });
        this.fetchRestrictions();
    },
    async fetchRestrictions() {
        try {
            const resModel = this?.env?.model?.config?.resModel;
            const result = await this.orm.call(
                "access.management",
                "get_remove_options",
                [1, resModel]
            );
            const restrictionKeys = Object.keys(this.restrictionFlags);
            result.forEach((item) => {
                if (restrictionKeys.includes(item)) {
                    this.restrictionFlags[item] = false
                }
            });

        } catch (error) {
            console.error("Failed to fetch restrictions:", error);
        }
    },
});
