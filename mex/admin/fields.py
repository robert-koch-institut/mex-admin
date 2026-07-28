from mex.common.fields import (
    ALL_MODEL_CLASSES_BY_NAME,
    ALL_TYPES_BY_FIELDS_BY_CLASS_NAMES,
    REFERENCE_FIELDS_BY_CLASS_NAME,
)
from mex.common.types import MERGED_IDENTIFIER_CLASSES
from mex.common.utils import contains_any_types, get_all_fields

# TODO(ND): Get these from mex.common.fields when upgrading to mex-common:1.14

# allowed entity types grouped for reference fields
REFERENCED_ENTITY_TYPES_BY_FIELD_BY_CLASS_NAME = {
    class_name: {
        field_name: sorted(
            identifier_class.__name__.removesuffix("Identifier")
            for identifier_class in MERGED_IDENTIFIER_CLASSES
            if contains_any_types(
                get_all_fields(ALL_MODEL_CLASSES_BY_NAME[class_name])[field_name],
                identifier_class,
            )
        )
        for field_name in field_names
    }
    for class_name, field_names in REFERENCE_FIELDS_BY_CLASS_NAME.items()
}

# stringified allowed types grouped by field and class names
STRINGIFIED_TYPES_BY_FIELD_BY_CLASS_NAME = {
    class_name: {
        field_name: REFERENCED_ENTITY_TYPES_BY_FIELD_BY_CLASS_NAME[class_name].get(
            field_name, sorted(str(field_type.__name__) for field_type in field_types)
        )
        for field_name, field_types in fields.items()
    }
    for class_name, fields in ALL_TYPES_BY_FIELDS_BY_CLASS_NAMES.items()
}
