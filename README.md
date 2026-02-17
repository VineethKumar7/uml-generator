# UML Domain Model Generator

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

Generate **UML Class Diagrams** and **Graph Schemas** (Neo4j property graphs) from simple YAML definitions. Outputs XMI, PlantUML, PNG, JPEG, and SVG.

Perfect for:
- 📚 Students creating UML diagrams for exams (including EWADIS!)
- 🏗️ Software architects documenting domain models
- 🚀 Quick prototyping of data models
- 📊 Neo4j/Graph database schema design

## Features

- ✅ **Simple YAML input** — Human-readable model definitions
- ✅ **Multiple output formats** — XMI, PlantUML, PNG, JPEG, SVG
- ✅ **Full UML support** — Classes, attributes, associations, compositions, aggregations, enumerations, inheritance
- ✅ **Graph Schema support** — Generate Neo4j property graph schemas with automatic direction detection
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
    fromRole: person        # Role on BOTH ends (mandatory!)
    toRole: contracts       # What Contract is from Person's view
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
# ⚠️ ALWAYS include fromRole AND toRole on BOTH ends!
associations:
  # Simple association - roles on BOTH ends
  - from: Customer
    to: Order
    fromRole: customer       # What Customer is from Order's view
    toRole: orders           # What Order is from Customer's view
    fromMultiplicity: "1"
    toMultiplicity: "0..*"
    type: association
  
  # Composition (◆) - child cannot exist without parent
  - from: Order
    to: OrderItem
    fromRole: order          # What Order is from OrderItem's view
    toRole: items            # What OrderItem is from Order's view
    fromMultiplicity: "1"
    toMultiplicity: "1..*"
    type: composition
  
  # Aggregation (◇) - child can exist independently
  - from: ShoppingCart
    to: Product
    fromRole: cart           # What ShoppingCart is from Product's view
    toRole: products         # What Product is from ShoppingCart's view
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

### ⚠️ Role Naming Convention (MANDATORY)

**Every association MUST have role names on BOTH ends:**

```yaml
associations:
  - from: Authority
    to: Building
    fromRole: authority    # ← REQUIRED: What Authority is from Building's view
    toRole: buildings      # ← REQUIRED: What Building is from Authority's view
    fromMultiplicity: "1"
    toMultiplicity: "1..*"
```

**Rule:** The role name describes what that class is **FROM THE OTHER CLASS'S PERSPECTIVE**.

| From | To | fromRole | toRole | Explanation |
|------|-----|----------|--------|-------------|
| Authority | Building | `authority` | `buildings` | Building sees "my authority", Authority sees "my buildings" |
| Person | Contract | `employee` | `contracts` | Contract sees "my employee", Person sees "my contracts" |
| Order | Item | `order` | `items` | Item sees "my order", Order sees "my items" |

**Output format:** Roles are prefixed with `-` (private visibility) in the diagram:
```
Authority "- authority 1" -- "- buildings 1..*" Building
```

**❌ WRONG (missing roles):**
```yaml
- from: Authority
  to: Building
  name: adds           # Only association name, no roles!
  fromMultiplicity: "1"
  toMultiplicity: "1..*"
```

**✅ CORRECT (both roles):**
```yaml
- from: Authority
  to: Building
  fromRole: authority
  toRole: buildings
  fromMultiplicity: "1"
  toMultiplicity: "1..*"
```

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
  --graph               Generate Graph Schema (Neo4j property graph)
  --graph-rules         Show Graph Schema conversion rules
  --example             Show example YAML format
  --help                Show help
```

## Graph Schema Generation

Generate Neo4j property graph schemas from the same YAML input used for UML diagrams.

### Usage

```bash
# Generate Graph Schema PNG
./uml-gen model.yaml --graph --png

# Show conversion rules
./uml-gen --graph-rules
```

### What It Does

The `--graph` flag automatically converts your OO/UML model to a Graph Schema:

| OO Schema | Graph Schema |
|-----------|--------------|
| Abstract classes | **Removed** (properties copied to children) |
| Concrete inheritance | **Flattened** (properties AND relationships copied) |
| Role names (`purchases`) | Converted to `HAS_PURCHASE` format |
| Composition (◆) | Becomes `CONTAINS` |
| Multiplicities | **Removed** (not used in graph schemas) |
| Arrowheads | **Removed** (direction shown in text: ► ▼ ◄ ▲) |

### Automatic Direction Detection

The tool uses a **two-pass approach** to automatically determine the correct direction symbol:

1. **First pass**: Render the diagram as SVG
2. **Parse positions**: Extract X,Y coordinates of each class from SVG
3. **Calculate directions**: Determine relative positions (right, down, etc.)
4. **Second pass**: Generate final diagram with correct symbols (► ▼ ◄ ▲)

This ensures the direction symbols always match the actual visual layout!

### Example Output

```
Person ── HAS_FRIEND ► ── Person (self-loop)
Person ── HAS_PURCHASE ▼ ── Purchase (down)
Purchase ── HAS_PRODUCT ► ── Product (right)
Category ── CONTAINS ▼ ── Product (down)
```

### Graph Schema Features

- 🟢 **Green node colors** — Distinguishes from UML (yellow)
- 📐 **Straight lines** — Using polyline layout
- ➡️ **Direction in text** — No arrowheads on lines, direction shown as ► ▼ ◄ ▲
- 🔄 **Inheritance flattening** — Subclasses get parent's properties AND relationships
- 📝 **Relationship naming** — Auto-converts role names to `HAS_X` format

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

| Rule | Value | Why |
|------|-------|-----|
| Top-to-bottom layout | default | Prevents label overlap (left-to-right causes collisions) |
| Node separation | 100px | Gives room for association labels |
| Rank separation | 80px | Vertical spacing between hierarchy levels |
| Class font | 11px | Readable class names |
| Attribute font | 10px | Smaller for attributes |
| Role label font | 9px | Smallest - prevents overlap on association lines |
| Scale | 1.2 @ 150 DPI | Good resolution without excessive file size |
| Yellow background | #FFFFCC | Matches Astah's default class color |
| Package frame | `pkg ModelName` | Matches Astah conventions |

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
