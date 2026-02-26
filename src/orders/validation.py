"""
Order Validation Rules Engine
Validates orders against business rules
"""

from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum


class ValidationSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class ValidationResult:
    """Result of a validation check"""
    passed: bool
    severity: ValidationSeverity
    code: str
    message: str
    field: Optional[str] = None
    suggestion: Optional[str] = None


class OrderValidationRule:
    """Base class for validation rules"""
    
    def __init__(self, code: str, message: str, severity: ValidationSeverity = ValidationSeverity.ERROR):
        self.code = code
        self.message = message
        self.severity = severity
    
    def validate(self, order) -> ValidationResult:
        raise NotImplementedError


class MinimumOrderValueRule(OrderValidationRule):
    """Check minimum order value"""
    
    def __init__(self, min_value: float = 5.0):
        super().__init__(
            code="MIN_ORDER_VALUE",
            message=f"Minimum order value is ${min_value:.2f}",
            severity=ValidationSeverity.ERROR
        )
        self.min_value = min_value
    
    def validate(self, order) -> ValidationResult:
        if order.subtotal < self.min_value:
            return ValidationResult(
                passed=False,
                severity=self.severity,
                code=self.code,
                message=self.message,
                suggestion=f"Add more items to reach ${self.min_value:.2f} minimum"
            )
        return ValidationResult(passed=True, severity=self.severity, code=self.code, message="OK")


class MaximumOrderValueRule(OrderValidationRule):
    """Check maximum order value"""
    
    def __init__(self, max_value: float = 200.0):
        super().__init__(
            code="MAX_ORDER_VALUE",
            message=f"Maximum order value is ${max_value:.2f}",
            severity=ValidationSeverity.ERROR
        )
        self.max_value = max_value
    
    def validate(self, order) -> ValidationResult:
        if order.total > self.max_value:
            return ValidationResult(
                passed=False,
                severity=self.severity,
                code=self.code,
                message=self.message,
                suggestion="Consider splitting into multiple orders"
            )
        return ValidationResult(passed=True, severity=self.severity, code=self.code, message="OK")


class RequiredCustomerInfoRule(OrderValidationRule):
    """Check required customer information"""
    
    def __init__(self):
        super().__init__(
            code="CUSTOMER_INFO_REQUIRED",
            message="Customer name is required",
            severity=ValidationSeverity.ERROR
        )
    
    def validate(self, order) -> ValidationResult:
        if not order.customer_name:
            return ValidationResult(
                passed=False,
                severity=self.severity,
                code=self.code,
                message="Please provide a name for the order",
                field="customer_name",
                suggestion="What name should I put this order under?"
            )
        return ValidationResult(passed=True, severity=self.severity, code=self.code, message="OK")


class FlavorRequiredRule(OrderValidationRule):
    """Check that wings have flavors"""
    
    def __init__(self):
        super().__init__(
            code="FLAVOR_REQUIRED",
            message="Wings require a flavor selection",
            severity=ValidationSeverity.ERROR
        )
    
    def validate(self, order) -> ValidationResult:
        for item in order.items:
            if item.category == 'wings' and not item.flavor:
                return ValidationResult(
                    passed=False,
                    severity=self.severity,
                    code=self.code,
                    message=f"{item.name} needs a flavor",
                    field=f"items.{item.id}.flavor",
                    suggestion=f"What flavor for your {item.name}?"
                )
        return ValidationResult(passed=True, severity=self.severity, code=self.code, message="OK")


class ComboValidationRule(OrderValidationRule):
    """Validate combo deals"""
    
    def __init__(self):
        super().__init__(
            code="COMBO_VALID",
            message="Combo requirements not met",
            severity=ValidationSeverity.WARNING
        )
    
    def validate(self, order) -> ValidationResult:
        # Check if combo eligible (wings + side + drink)
        has_wings = any(item.category == 'wings' for item in order.items)
        has_side = any(item.category == 'sides' for item in order.items)
        has_drink = any(item.category == 'drinks' for item in order.items)
        
        if has_wings and not (has_side and has_drink):
            return ValidationResult(
                passed=True,  # Still valid, just a suggestion
                severity=ValidationSeverity.INFO,
                code="COMBO_SUGGESTION",
                message="Add a side and drink to make it a combo and save $2!",
                suggestion="Would you like to add fries and a drink for a combo?"
            )
        
        return ValidationResult(passed=True, severity=self.severity, code=self.code, message="OK")


class MaximumItemsRule(OrderValidationRule):
    """Check maximum number of items"""
    
    def __init__(self, max_items: int = 20):
        super().__init__(
            code="MAX_ITEMS",
            message=f"Maximum {max_items} items per order",
            severity=ValidationSeverity.ERROR
        )
        self.max_items = max_items
    
    def validate(self, order) -> ValidationResult:
        if order.item_count > self.max_items:
            return ValidationResult(
                passed=False,
                severity=self.severity,
                code=self.code,
                message=self.message,
                suggestion="For large orders, please call the restaurant directly"
            )
        return ValidationResult(passed=True, severity=self.severity, code=self.code, message="OK")


class DuplicateItemRule(OrderValidationRule):
    """Check for potential duplicate items"""
    
    def __init__(self):
        super().__init__(
            code="DUPLICATE_ITEMS",
            message="Potential duplicate items detected",
            severity=ValidationSeverity.WARNING
        )
    
    def validate(self, order) -> ValidationResult:
        item_names = {}
        for item in order.items:
            name_lower = item.name.lower()
            if name_lower in item_names:
                return ValidationResult(
                    passed=True,
                    severity=ValidationSeverity.WARNING,
                    code=self.code,
                    message=f"You have multiple {item.name} entries",
                    suggestion="Would you like me to combine these into one?"
                )
            item_names[name_lower] = item
        
        return ValidationResult(passed=True, severity=self.severity, code=self.code, message="OK")


class OrderValidator:
    """
    Order Validation Engine
    Runs all validation rules and aggregates results
    """
    
    def __init__(self):
        self.rules: List[OrderValidationRule] = []
        self._register_default_rules()
    
    def _register_default_rules(self):
        """Register default Wingstop validation rules"""
        self.rules.extend([
            MinimumOrderValueRule(min_value=5.0),
            MaximumOrderValueRule(max_value=200.0),
            RequiredCustomerInfoRule(),
            FlavorRequiredRule(),
            ComboValidationRule(),
            MaximumItemsRule(max_items=20),
            DuplicateItemRule()
        ])
    
    def add_rule(self, rule: OrderValidationRule):
        """Add custom validation rule"""
        self.rules.append(rule)
    
    def validate(self, order) -> Dict:
        """
        Validate order against all rules
        
        Returns:
            Dict with validation results
        """
        results = []
        errors = []
        warnings = []
        info = []
        
        for rule in self.rules:
            result = rule.validate(order)
            results.append(result)
            
            if not result.passed:
                if result.severity == ValidationSeverity.ERROR:
                    errors.append(result)
                elif result.severity == ValidationSeverity.WARNING:
                    warnings.append(result)
            elif result.severity == ValidationSeverity.INFO:
                info.append(result)
        
        can_submit = len(errors) == 0
        
        return {
            "valid": can_submit,
            "can_submit": can_submit,
            "errors": [
                {"code": r.code, "message": r.message, "field": r.field, "suggestion": r.suggestion}
                for r in errors
            ],
            "warnings": [
                {"code": r.code, "message": r.message, "suggestion": r.suggestion}
                for r in warnings
            ],
            "suggestions": [
                {"code": r.code, "message": r.message, "suggestion": r.suggestion}
                for r in info
            ],
            "missing_fields": list(set(r.field for r in errors if r.field)),
            "error_count": len(errors),
            "warning_count": len(warnings)
        }
    
    def validate_field(self, order, field: str) -> Optional[ValidationResult]:
        """Validate specific field"""
        for rule in self.rules:
            result = rule.validate(order)
            if result.field == field:
                return result
        return None
    
    def get_validation_summary(self, order) -> str:
        """Get human-readable validation summary"""
        result = self.validate(order)
        
        lines = []
        
        if result['can_submit']:
            lines.append("Order is ready to submit!")
        else:
            lines.append("Please fix the following before submitting:")
        
        for error in result['errors']:
            lines.append(f"  Error: {error['message']}")
        
        for warning in result['warnings']:
            lines.append(f"  Warning: {warning['message']}")
        
        for suggestion in result['suggestions']:
            lines.append(f"  Tip: {suggestion['message']}")
        
        return "\n".join(lines)


class OrderRequirementsChecker:
    """
    Check order requirements progressively
    Helps guide the conversation
    """
    
    REQUIREMENTS = [
        {"field": "items", "check": lambda o: not o.is_empty, "prompt": "What would you like to order?"},
        {"field": "flavors", "check": lambda o: all(item.flavor for item in o.items if item.category == 'wings'), 
         "prompt": "What flavor would you like for your wings?"},
        {"field": "customer_name", "check": lambda o: bool(o.customer_name), 
         "prompt": "What name should I put this order under?"},
    ]
    
    def get_next_requirement(self, order) -> Optional[Dict]:
        """Get the next unmet requirement"""
        for req in self.REQUIREMENTS:
            if not req['check'](order):
                return req
        return None
    
    def get_progress(self, order) -> Dict:
        """Get order completion progress"""
        total = len(self.REQUIREMENTS)
        completed = sum(1 for req in self.REQUIREMENTS if req['check'](order))
        
        return {
            "completed": completed,
            "total": total,
            "percent": int((completed / total) * 100),
            "is_complete": completed == total,
            "next_step": self.get_next_requirement(order)
        }
