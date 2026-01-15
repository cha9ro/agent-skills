# Domain Layer Patterns

The domain layer is the innermost layer containing core business logic. Uses Pydantic for validation and immutability.

> **Note:** While pure DDD suggests zero external dependencies in the domain layer, we pragmatically use Pydantic for its powerful validation, serialization, and immutability features.

## Entities

Entities have identity and lifecycle. The key characteristic is that **two entities are the same if their IDs match, even if other attributes differ**. Override `__eq__` and `__hash__` to compare by ID only:

```python
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from uuid import UUID, uuid4


class Entity(BaseModel):
    """Base class for all entities."""

    id: UUID = Field(default_factory=uuid4)

    def __eq__(self, other: object) -> bool:
        """Compare entities by ID only, not by attributes."""
        if not isinstance(other, Entity):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        """Hash by ID for use in sets and dicts."""
        return hash(self.id)


class User(Entity):
    """User entity with business logic."""

    name: str = Field(min_length=1)
    email: str
    updated_at: datetime = Field(default_factory=datetime.now)

    def change_name(self, new_name: str) -> None:
        """Change user's name (business logic method)."""
        if not new_name.strip():
            raise ValueError("Name cannot be empty")
        self.name = new_name
        self.updated_at = datetime.now()

    def change_email(self, new_email: str) -> None:
        """Change user's email (business logic method)."""
        if "@" not in new_email:
            raise ValueError("Invalid email format")
        self.email = new_email
        self.updated_at = datetime.now()
```

### Entity Best Practices

- **Use methods for state changes**: Never set attributes directly (e.g., `user.name = "new"`). Instead, use methods like `user.change_name("new")` to encapsulate business logic.
- **Encapsulate business rules**: All state-changing operations should go through methods that enforce business rules.
- **ID-based equality**: Entities are equal if their IDs match, regardless of attribute values.

## Value Objects

Value Objects are **immutable objects where equality is based on all attributes, not identity**. If all attributes match, the objects are considered identical. Use `frozen=True` with `ConfigDict` to enforce immutability:

```python
from pydantic import BaseModel, Field, ConfigDict


class Money(BaseModel):
    """Monetary value with currency (immutable)."""

    model_config = ConfigDict(frozen=True)  # Makes the object immutable

    amount: int = Field(ge=0, description="Amount in smallest unit (cents)")
    currency: str = Field(pattern=r"^[A-Z]{3}$", description="ISO 4217 currency code")

    def add(self, other: "Money") -> "Money":
        """Add two money values (returns new instance)."""
        if self.currency != other.currency:
            raise ValueError("Cannot add money with different currencies")
        return Money(amount=self.amount + other.amount, currency=self.currency)

    def subtract(self, other: "Money") -> "Money":
        """Subtract money values (returns new instance)."""
        if self.currency != other.currency:
            raise ValueError("Cannot subtract money with different currencies")
        if self.amount < other.amount:
            raise ValueError("Insufficient funds")
        return Money(amount=self.amount - other.amount, currency=self.currency)


class Email(BaseModel):
    """Email address value object with validation."""

    model_config = ConfigDict(frozen=True)

    value: str = Field(pattern=r"^[\w.-]+@[\w.-]+\.\w+$")

    def domain(self) -> str:
        """Extract domain from email."""
        return self.value.split("@")[1]


class Address(BaseModel):
    """Physical address value object."""

    model_config = ConfigDict(frozen=True)

    street: str = Field(min_length=1)
    city: str = Field(min_length=1)
    postal_code: str = Field(min_length=1)
    country: str = Field(min_length=2, max_length=2, description="ISO 3166-1 alpha-2")

    def full_address(self) -> str:
        """Get formatted full address."""
        return f"{self.street}, {self.city} {self.postal_code}, {self.country}"
```

### Value Object Best Practices

- **Always use `frozen=True`**: This prevents modification after creation and ensures immutability.
- **Return new instances**: Operations like `add()` or `subtract()` should return new Value Objects, not modify the existing one.
- **Equality by value**: Two Value Objects with the same attributes are considered equal (Pydantic does this automatically).

## Repository Interfaces (Ports)

Define abstract interfaces for persistence. Infrastructure implements these:

```python
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

T = TypeVar("T")


class Repository(ABC, Generic[T]):
    @abstractmethod
    def find_by_id(self, id: str) -> T | None: ...

    @abstractmethod
    def find_all(self) -> list[T]: ...

    @abstractmethod
    def save(self, entity: T) -> T: ...

    @abstractmethod
    def delete(self, id: str) -> None: ...


class UserRepository(Repository["User"], ABC):
    @abstractmethod
    def find_by_email(self, email: str) -> "User | None": ...
```

## Domain Services

Stateless operations that don't belong to a single entity:

```python
from pydantic import BaseModel


class PricingService(BaseModel):
    """Domain service for price calculations."""

    tax_rate: float = 0.1

    def calculate_total(self, subtotal: Money, discount: Money) -> Money:
        net = subtotal.add(Money(amount=-discount.amount, currency=subtotal.currency))
        tax = Money(amount=int(net.amount * self.tax_rate), currency=net.currency)
        return net.add(tax)
```

## Domain Events

Use frozen models for immutable events:

```python
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import uuid4


class DomainEvent(BaseModel):
    """Base class for domain events."""

    model_config = {"frozen": True}

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    occurred_at: datetime = Field(default_factory=datetime.utcnow)


class UserCreated(DomainEvent):
    user_id: str
    email: str
```

## Validation Patterns

Leverage Pydantic's built-in validators:

```python
from pydantic import BaseModel, Field, field_validator


class Product(BaseModel):
    model_config = {"frozen": True}

    name: str = Field(min_length=1, max_length=100)
    price: int = Field(gt=0)
    sku: str = Field(pattern=r"^[A-Z]{3}-\d{4}$")

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Name cannot be blank")
        return v.strip()
```

## Domain Exceptions

Define domain-specific exceptions that represent business rule violations:

```python
class DomainException(Exception):
    """Base exception for domain errors."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class EntityNotFoundError(DomainException):
    """Raised when an entity is not found."""

    def __init__(self, entity_type: str, entity_id: str):
        self.entity_type = entity_type
        self.entity_id = entity_id
        super().__init__(f"{entity_type} with id '{entity_id}' not found")


class ValidationError(DomainException):
    """Raised when domain validation fails."""

    def __init__(self, message: str, field: str | None = None):
        self.field = field
        super().__init__(message)


class DuplicateEntityError(DomainException):
    """Raised when attempting to create a duplicate entity."""

    def __init__(self, entity_type: str, field: str, value: str):
        self.entity_type = entity_type
        self.field = field
        self.value = value
        super().__init__(f"{entity_type} with {field} '{value}' already exists")


class BusinessRuleViolationError(DomainException):
    """Raised when a business rule is violated."""

    pass
```

## Important Implementation Techniques

### 1. Separation of Validation and Business Logic

**Pydantic's role**: Type safety, format validation, and structural constraints.

**Domain logic's role**: Business rules and domain-specific validation.

```python
from pydantic import BaseModel, Field


class Order(BaseModel):
    """Order entity with clear separation of concerns."""

    id: str
    customer_id: str
    items: list[str] = Field(min_length=1)  # Pydantic: structural validation
    status: str = Field(pattern=r"^(pending|confirmed|shipped|delivered)$")

    def can_cancel(self) -> bool:
        """Business logic: complex rule that Pydantic shouldn't handle."""
        return self.status in ["pending", "confirmed"]

    def cancel(self) -> None:
        """Business logic: state transition with domain rules."""
        if not self.can_cancel():
            raise BusinessRuleViolationError(
                f"Cannot cancel order with status '{self.status}'"
            )
        self.status = "cancelled"

    def ship(self, tracking_number: str) -> None:
        """Business logic: status transition with validation."""
        if self.status != "confirmed":
            raise BusinessRuleViolationError(
                "Can only ship confirmed orders"
            )
        if not tracking_number:
            raise ValueError("Tracking number required")
        self.status = "shipped"
```

**Guidelines:**
- **Pydantic validation**: String length, numeric ranges, regex patterns, required fields, type checking
- **Domain logic**: "Is stock available?", "Can this state transition happen?", "Is this operation allowed for this user role?"

### 2. Converting from Database Models with `model_validate`

Use `model_validate()` (formerly `parse_obj()` or `from_orm()`) to convert ORM/database models to domain entities in the repository layer:

```python
from pydantic import BaseModel, ConfigDict
from typing import Protocol


# Database model (Infrastructure layer)
class UserDTO:
    """SQLAlchemy or other ORM model."""
    def __init__(self, id: str, name: str, email: str):
        self.id = id
        self.name = name
        self.email = email


# Domain entity
class User(BaseModel):
    """Domain model with validation."""
    model_config = ConfigDict(from_attributes=True)  # Enable ORM mode

    id: str
    name: str
    email: str

    def change_name(self, new_name: str) -> None:
        self.name = new_name


# Repository implementation (Infrastructure layer)
class UserRepositoryImpl:
    def find_by_id(self, user_id: str) -> User | None:
        # Fetch from database
        db_user = self._fetch_from_db(user_id)  # Returns UserDTO
        if not db_user:
            return None

        # Convert DTO to domain model using model_validate
        return User.model_validate(db_user)

    def _fetch_from_db(self, user_id: str) -> UserDTO | None:
        # Database query logic here
        ...
```

**Benefits:**
- Automatic field mapping from ORM models to Pydantic models
- Type conversion and validation during transformation
- Clean separation between persistence and domain concerns

### 3. Private Attributes with `PrivateAttr`

Use `PrivateAttr` for internal state that shouldn't be serialized or exposed externally:

```python
from pydantic import BaseModel, PrivateAttr, Field
from datetime import datetime


class Order(BaseModel):
    """Order with internal caching."""

    id: str
    items: list[str]
    created_at: datetime = Field(default_factory=datetime.now)

    # Private attribute: not included in serialization or validation
    _calculated_total: int | None = PrivateAttr(default=None)
    _cache: dict = PrivateAttr(default_factory=dict)

    def calculate_total(self) -> int:
        """Calculate total with caching."""
        if self._calculated_total is None:
            # Expensive calculation
            self._calculated_total = sum(
                self._get_item_price(item) for item in self.items
            )
        return self._calculated_total

    def _get_item_price(self, item: str) -> int:
        """Internal helper using cache."""
        if item not in self._cache:
            # Fetch price from somewhere
            self._cache[item] = len(item) * 100  # Example calculation
        return self._cache[item]


# Usage
order = Order(id="123", items=["apple", "banana"])
total = order.calculate_total()

# Private attributes are not included when serializing
print(order.model_dump())  # Only shows: id, items, created_at
```

**When to use `PrivateAttr`:**
- Caching computed values
- Temporary state during complex operations
- Internal flags or metadata
- Anything that shouldn't be part of the domain model's external interface

## Best Practices for DDD with Pydantic

### 1. Use Methods Instead of Direct Attribute Assignment

❌ **Bad:** Direct attribute modification bypasses business logic
```python
user.name = "New Name"  # No validation, no business rules
user.status = "banned"  # Could violate state transition rules
```

✅ **Good:** Methods encapsulate business logic
```python
user.change_name("New Name")  # Can enforce rules
user.ban(reason="spam")       # Can validate state transitions
```

### 2. Separate DTOs from Domain Models

Keep API/Request DTOs separate from domain entities to prevent API changes from affecting domain logic:

```python
# Presentation layer - API Request DTO
class CreateUserRequest(BaseModel):
    """API request model - can change with API versions."""
    name: str
    email: str
    marketing_consent: bool = False


# Domain layer - Entity
class User(Entity):
    """Domain model - stable, contains business logic."""
    name: str
    email: str
    status: str = "active"
    created_at: datetime = Field(default_factory=datetime.now)

    def activate(self) -> None:
        """Business logic."""
        self.status = "active"


# Application layer - Use case
class CreateUserUseCase:
    def execute(self, request: CreateUserRequest) -> User:
        """Convert DTO to domain model."""
        user = User(
            name=request.name,
            email=request.email,
        )
        # Apply business logic
        user.activate()
        return user
```

**Benefits:**
- API changes don't affect domain models
- Domain models stay focused on business logic
- Clear boundaries between layers

### 3. Keep Domain Models Rich with Behavior

Don't create anemic domain models. Add business logic as methods:

```python
class BankAccount(Entity):
    """Rich domain model with behavior."""

    balance: int = Field(ge=0)
    currency: str
    status: str = "active"

    def deposit(self, amount: Money) -> None:
        """Business logic for deposits."""
        if self.status != "active":
            raise BusinessRuleViolationError("Account is not active")
        if amount.currency != self.currency:
            raise ValueError("Currency mismatch")
        self.balance += amount.amount

    def withdraw(self, amount: Money) -> None:
        """Business logic for withdrawals."""
        if self.status != "active":
            raise BusinessRuleViolationError("Account is not active")
        if amount.currency != self.currency:
            raise ValueError("Currency mismatch")
        if self.balance < amount.amount:
            raise BusinessRuleViolationError("Insufficient funds")
        self.balance -= amount.amount

    def close(self) -> None:
        """Close account with business rules."""
        if self.balance > 0:
            raise BusinessRuleViolationError("Cannot close account with positive balance")
        self.status = "closed"
```

## Rules

1. **Use Pydantic BaseModel** - For entities, value objects, and domain events
2. **frozen=True for value objects** - Ensures immutability
3. **Validation in models** - Use Field constraints and validators for structural/format validation
4. **Business logic in methods** - Entities should have rich behavior, not just data
5. **Repository interfaces only** - Implementations live in infrastructure
6. **Domain exceptions** - Define business error types in domain layer
7. **Separate DTOs from domain models** - Don't let API changes affect domain logic
8. **Use model_validate** - Convert database/ORM models to domain models in repositories
9. **PrivateAttr for internal state** - Keep implementation details private
