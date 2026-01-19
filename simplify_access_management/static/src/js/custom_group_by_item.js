/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { onWillStart,onMounted } from "@odoo/owl";
import {CustomGroupByItem} from "@web/search/custom_group_by_item/custom_group_by_item";

patch(CustomGroupByItem.prototype,{
    setup(){
        super.setup(...arguments);
        this.orm = useService("orm"); 
        this.hidden_fields = [];
        onMounted(async () => {   
            // Get hidden fields by action id.
            // const res = await this.orm.call("access.management", "get_hidden_field", ["",this?.env?.searchModel?.resModel]); 
            this.hidden_fields = await this.orm.call("access.management", "get_hidden_field_by_action", ["",this.env?.config?.actionId]); 
            this.render();
        });
    }
});