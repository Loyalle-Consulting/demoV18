import { MultiRecordSelectorBits } from "../record_selectors/multi_record_selector";
import { _t } from "@web/core/l10n/translation";
import { formatAST, toPyValue } from "@web/core/py_js/py_utils";
import { Expression } from "./condition_tree";
import { RecordSelectorBits } from "../record_selectors/record_selector";

// changed 1 to 0
export const isId = (val) => Number.isInteger(val) && val >= 0;

export const getFormat = (val, displayNames) => {
    let text;
    let colorIndex; 
    if (isId(val)) {
        text =
            typeof displayNames[val] === "string"
                ? displayNames[val]
                : _t("Inaccessible/missing record ID: %s", val);
        colorIndex = typeof displayNames[val] === "string" ? 0 : 2; // 0 = grey, 2 = orange
    } else {
        text =
            val instanceof Expression
                ? String(val)
                : _t("Invalid record ID: %s", formatAST(toPyValue(val)));
        colorIndex = val instanceof Expression ? 2 : 1; // 1 = red
    }
    return { text, colorIndex };
};

export class DomainSelectorAutocomplete extends MultiRecordSelectorBits {
    static props = {
        ...MultiRecordSelectorBits.props,
        resIds: true, //resIds could be an array of ids or an array of expressions
    }
    getIds(props = this.props) {
        return props.resIds.filter((val) => isId(val));
    }

    getTags(props, displayNames) {
        return props.resIds.map((val, index) => {
            const { text, colorIndex } = getFormat(val, displayNames);
            return {
                text,
                colorIndex,
                onDelete: () => {
                    this.props.update([
                        ...this.props.resIds.slice(0, index),
                        ...this.props.resIds.slice(index + 1),
                    ]);
                },
            };
        });
    }
} 

export class DomainSelectorSingleAutocomplete extends RecordSelectorBits {
    static props = {
        ...RecordSelectorBits.props,
        resId: true,
    };

    getDisplayName(props = this.props, displayNames) {
        const { resId } = props;
        if (resId === false) {
            return "";
        }
        const { text } = getFormat(resId, displayNames);
        return text;
    }

    getIds(props = this.props) {
        if (isId(props.resId)) {
            return [props.resId];
        }
        return [];
    }
}
