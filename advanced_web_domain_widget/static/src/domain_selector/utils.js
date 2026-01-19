import { getDefaultValue } from "../tree_editor/tree_editor_value_editors";
import { getDomainDisplayedOperators } from "./domain_selector_operator_editor";
import { useService } from "@web/core/utils/hooks";
import { domainFromTree, condition } from "../tree_editor/condition_tree";
import { getDefaultPath } from "../tree_editor/utils";

export function getDefaultCondition(fieldDefs) {
    const defaultPath = getDefaultPath(fieldDefs);
    const fieldDef = fieldDefs[defaultPath];
    const operator = getDomainDisplayedOperators(fieldDef)[0];
    const value = getDefaultValue(fieldDef, operator);
    return condition(fieldDef.name, operator, value);
}

export function getDefaultDomain(fieldDefs) {
    return domainFromTree(getDefaultCondition(fieldDefs));
}

export function useGetDefaultLeafDomain() {
    const fieldService = useService("field");
    return async (resModel) => {
        const fieldDefs = await fieldService.loadFields(resModel);
        return getDefaultDomain(fieldDefs);
    };
}
