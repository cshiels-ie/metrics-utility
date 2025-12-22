"""
Configuration form widget for TUI.

Dynamically generates form fields based on schema with validation.
"""

from typing import Dict, List

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.validation import Number
from textual.widgets import Checkbox, Input, Label, Select, Static

from ..config.manager import ConfigManager
from ..config.schema import CONFIG_SCHEMA, ConfigField, FieldCategory, FieldType


class ConfigFormField(Vertical):
    """Single configuration field with label and input"""

    def __init__(
        self,
        field: ConfigField,
        config_manager: ConfigManager,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.field = field
        self.config_manager = config_manager
        self.input_widget = None

    def compose(self) -> ComposeResult:
        """Create field widgets"""
        # Label with description
        label_text = self.field.display_name
        if self.field.required:
            label_text = f'{label_text} *'

        yield Label(label_text, classes='field-label')

        # Get current value
        current_value = self.config_manager.get(self.field.key)

        # Create appropriate input widget based on field type
        if self.field.field_type == FieldType.BOOLEAN:
            self.input_widget = Checkbox(
                '',
                value=bool(current_value) if current_value is not None else False,
                id=f'input_{self.field.key}',
            )
        elif self.field.field_type == FieldType.SELECT:
            if self.field.options:
                options = [(opt, opt) for opt in self.field.options]
                self.input_widget = Select(
                    options=options,
                    value=current_value or Select.BLANK,
                    allow_blank=not self.field.required,
                    id=f'input_{self.field.key}',
                )
        elif self.field.field_type == FieldType.INTEGER:
            validators = []
            if self.field.validator:
                # Use Number validator for integers
                validators.append(Number())

            self.input_widget = Input(
                value=str(current_value) if current_value is not None else '',
                placeholder=f'{self.field.default}' if self.field.default is not None else 'Enter number',
                type='integer',
                validators=validators,
                id=f'input_{self.field.key}',
            )
        elif self.field.field_type == FieldType.FLOAT:
            validators = []
            if self.field.validator:
                validators.append(Number(minimum=0))

            self.input_widget = Input(
                value=str(current_value) if current_value is not None else '',
                placeholder=f'{self.field.default}' if self.field.default is not None else 'Enter number',
                type='number',
                validators=validators,
                id=f'input_{self.field.key}',
            )
        elif self.field.field_type == FieldType.PASSWORD:
            self.input_widget = Input(
                value=str(current_value) if current_value else '',
                placeholder='Enter password',
                password=True,
                id=f'input_{self.field.key}',
            )
        else:  # STRING or MULTISELECT
            self.input_widget = Input(
                value=str(current_value) if current_value else '',
                placeholder=self.field.description,
                id=f'input_{self.field.key}',
            )

        yield self.input_widget

        # Help text
        if self.field.description:
            yield Static(self.field.description, classes='field-help', markup=False)

    def get_value(self):
        """Get current value from input widget"""
        if isinstance(self.input_widget, Checkbox):
            return self.input_widget.value
        elif isinstance(self.input_widget, Select):
            val = self.input_widget.value
            return val if val != Select.BLANK else None
        elif isinstance(self.input_widget, Input):
            val = self.input_widget.value
            if not val:
                return None

            # Parse based on field type
            if self.field.field_type == FieldType.INTEGER:
                try:
                    return int(val)
                except ValueError:
                    return None
            elif self.field.field_type == FieldType.FLOAT:
                try:
                    return float(val)
                except ValueError:
                    return None
            elif self.field.field_type == FieldType.MULTISELECT:
                # Parse comma-separated values
                return [v.strip() for v in val.split(',') if v.strip()]
            else:
                return val

        return None

    def set_value(self, value):
        """Set value in input widget"""
        if isinstance(self.input_widget, Checkbox):
            self.input_widget.value = bool(value)
        elif isinstance(self.input_widget, Select):
            self.input_widget.value = value or Select.BLANK
        elif isinstance(self.input_widget, Input):
            if value is None:
                self.input_widget.value = ''
            elif isinstance(value, list):
                # For multiselect, join with commas
                self.input_widget.value = ','.join(str(v) for v in value)
            else:
                self.input_widget.value = str(value)


class ConfigForm(Vertical):
    """Form containing multiple configuration fields"""

    CSS = """
    ConfigForm {
        padding: 1 2;
    }

    .field-label {
        margin-top: 1;
        text-style: bold;
    }

    .field-help {
        margin-bottom: 1;
        text-style: italic;
    }

    .category-header {
        background: $primary;
        padding: 1 2;
        margin: 1 0;
        text-style: bold;
    }
    """

    def __init__(
        self,
        category: FieldCategory,
        config_manager: ConfigManager,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.category = category
        self.config_manager = config_manager
        self.field_widgets: Dict[str, ConfigFormField] = {}

    def compose(self) -> ComposeResult:
        """Create form fields for category"""
        # Category header
        yield Static(f'[white]{self.category.value}[/white]', classes='category-header')

        # Get fields for this category
        fields = [f for f in CONFIG_SCHEMA if f.category == self.category]

        # Current config for checking dependencies
        current_config = self.config_manager.get_all()

        for field in fields:
            # Check if field should be visible based on dependencies
            if field.depends_on:
                visible = False
                for dep_key, dep_values in field.depends_on.items():
                    dep_value = current_config.get(dep_key)
                    if dep_value in dep_values:
                        visible = True
                        break

                if not visible:
                    continue

            # Create field widget
            field_widget = ConfigFormField(field, self.config_manager)
            self.field_widgets[field.key] = field_widget
            yield field_widget

    def get_values(self) -> Dict[str, any]:
        """Get all field values"""
        values = {}
        for key, field_widget in self.field_widgets.items():
            values[key] = field_widget.get_value()
        return values

    def set_values(self, values: Dict[str, any]) -> None:
        """Set field values"""
        for key, value in values.items():
            if key in self.field_widgets:
                self.field_widgets[key].set_value(value)

    def validate(self) -> List[str]:
        """
        Validate all fields in form.

        Returns:
            List of error messages (empty if valid)
        """
        errors = []
        values = self.get_values()

        for key, field_widget in self.field_widgets.items():
            field = field_widget.field
            value = values.get(key)

            # Check required fields
            if field.required and not value:
                errors.append(f'{field.display_name} is required')

            # Check field-specific validators
            if value and field.validator:
                try:
                    if not field.validator(value):
                        errors.append(f'{field.display_name} has invalid value')
                except Exception as e:
                    errors.append(f'{field.display_name} validation error: {e}')

            # Check select options
            if value and field.field_type == FieldType.SELECT:
                if field.options and value not in field.options:
                    errors.append(f'{field.display_name} must be one of: {", ".join(field.options)}')

        return errors
