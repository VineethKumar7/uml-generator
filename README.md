# UML Domain Model Generator

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

Generate UML Class Diagrams from simple YAML definitions. Outputs XMI, PlantUML, PNG, JPEG, and SVG.

Perfect for:
- 📚 Students creating UML diagrams for exams
- 🏗️ Software architects documenting domain models
- 🚀 Quick prototyping of data models

## Features

- ✅ **Simple YAML input** — Human-readable model definitions
- ✅ **Multiple output formats** — XMI, PlantUML, PNG, JPEG, SVG
- ✅ **Full UML support** — Classes, attributes, associations, compositions, aggregations, enumerations, inheritance
- ✅ **Astah compatible** — Generated XMI can be imported into Astah
- ✅ **Command-line tool** — Easy integration into workflows

## Installation

```bash
# Clone the repository
git clone https://github.com/VineethKumar7/uml-generator.git
cd uml-generator

# Install dependencies
pip install pyyaml

# (Optional) For image generation, Java is required
java -version
```

## Quick Start

### 1. Create a YAML model file

```yaml
# my_model.yaml
name: "My Domain Model"

enumerations:
  Status:
    - ACTIVE
    - INACTIVE

classes:
  Person:
    attributes:
      - name: firstName
        type: String
      - name: email
        type: String
  
  Contract:
    attributes:
      - name: id
        type: String
      - name: status
        type: Status

associations:
  - from: Person
    to: Contract
    name: has
    fromMultiplicity: "1"
    toMultiplicity: "0..*"
    type: association
```

### 2. Generate the diagram

```bash
# Generate PNG image
./uml-gen my_model.yaml --png

# Generate all formats
./uml-gen my_model.yaml --all

# Generate XMI for Astah import
./uml-gen my_model.yaml --xmi
```

### 3. Output

```
my_model.png      # Rendered diagram image
my_model.xmi      # XMI file for Astah/UML tools
my_model.puml     # PlantUML source
```

## YAML Schema Reference

### Complete Example

```yaml
name: "E-Commerce Domain Model"

# Enumerations (fixed value sets)
enumerations:
  OrderStatus:
    - PENDING
    - SHIPPED
    - DELIVERED
    - CANCELLED
  
  PaymentMethod:
    - CREDIT_CARD
    - PAYPAL
    - BANK_TRANSFER

# Classes with attributes
classes:
  Customer:
    attributes:
      - name: id
        type: String
        visibility: private    # private (-), public (+), protected (#)
      - name: email
        type: String
        visibility: private
      - name: registeredAt
        type: DateTime
        visibility: private
  
  Order:
    attributes:
      - name: orderId
        type: String
        visibility: private
      - name: status
        type: OrderStatus      # Reference to enum
        visibility: private
      - name: totalAmount
        type: Float
        visibility: private
  
  Product:
    abstract: true             # Abstract class
    attributes:
      - name: name
        type: String
      - name: price
        type: Float
  
  PhysicalProduct:
    attributes:
      - name: weight
        type: Float
      - name: dimensions
        type: String
  
  DigitalProduct:
    attributes:
      - name: downloadUrl
        type: String
      - name: fileSize
        type: Integer

# Associations between classes
associations:
  # Simple association
  - from: Customer
    to: Order
    name: places
    fromMultiplicity: "1"
    toMultiplicity: "0..*"
    type: association
  
  # Composition (◆) - child cannot exist without parent
  - from: Order
    to: OrderItem
    name: contains
    fromMultiplicity: "1"
    toMultiplicity: "1..*"
    type: composition
  
  # Aggregation (◇) - child can exist independently
  - from: ShoppingCart
    to: Product
    name: items
    fromMultiplicity: "1"
    toMultiplicity: "0..*"
    type: aggregation

# Inheritance (generalization)
generalizations:
  - parent: Product
    child: PhysicalProduct
  - parent: Product
    child: DigitalProduct
```

### Data Types

| Type | Description |
|------|-------------|
| `String` | Text values |
| `Integer` / `int` | Whole numbers |
| `Float` / `Double` | Decimal numbers |
| `Boolean` | True/false |
| `Date` | Date only |
| `DateTime` | Date and time |
| `Time` | Time only |

### Association Types

| Type | Symbol | Description |
|------|--------|-------------|
| `association` | — | Simple relationship |
| `composition` | ◆ | Strong ownership (child deleted with parent) |
| `aggregation` | ◇ | Weak ownership (child can exist independently) |

### Multiplicities

| Value | Meaning |
|-------|---------|
| `1` | Exactly one |
| `0..1` | Zero or one (optional) |
| `*` or `0..*` | Zero or more |
| `1..*` | One or more |
| `n..m` | Range (e.g., `2..5`) |

## Command Reference

```bash
uml-gen <model.yaml> [options]

Options:
  -o, --output <name>   Output base name (without extension)
  --png                 Generate PNG image
  --jpg, --jpeg         Generate JPEG image
  --svg                 Generate SVG image
  --xmi                 Generate XMI file (default)
  --plantuml            Generate PlantUML file
  --all                 Generate all formats
  --example             Show example YAML format
  --help                Show help
```

## Examples

See the `examples/` directory for sample YAML files:

- `cbs_domain_model.yaml` — Building permit system (exam example)
- `tss_domain_model.yaml` — Time sheet system
- `ecommerce_model.yaml` — E-commerce domain

## Importing to Astah

1. Generate XMI: `./uml-gen model.yaml --xmi`
2. Open Astah Professional
3. File → Import → XMI...
4. Select the generated `.xmi` file

> Note: Some Astah versions may have limited XMI import support. Use the PNG output as a reference for manual creation if needed.

## Layout Rules

The generator uses these rules for clean, readable diagrams:

| Rule | Why |
|------|-----|
| Top-to-bottom layout | Prevents label overlap (left-to-right causes collisions) |
| Node separation: 80px | Gives room for association labels |
| Rank separation: 60px | Vertical spacing between hierarchy levels |
| Single-line role labels | `"- roleName mult"` prevents text overlapping classes |
| Scale 1.2 @ 150 DPI | Good resolution without excessive file size |
| Smaller fonts (11/10px) | Reduces visual clutter |
| Yellow background (#FFFFCC) | Matches Astah's default class color |
| Package frame | `pkg ModelName` matches Astah conventions |

## Requirements

- Python 3.8+
- PyYAML (`pip install pyyaml`)
- Java 8+ (for image generation only)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Author

**Vineeth Kumar**
- GitHub: [@VineethKumar7](https://github.com/VineethKumar7)
- LinkedIn: [vineethkumar7](https://www.linkedin.com/in/vineethkumar7)

---

Made with ❤️ for the UML community
