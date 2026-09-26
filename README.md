# NovaCart — E-commerce Order & Fulfillment Platform

NovaCart is an evolving e-commerce order and fulfillment platform built to receive orders from multiple sales channels and process them through a centralized, reliable order lifecycle.

The project is being developed incrementally as an integrated **Forward Deployed Engineer (FDE) learning project**. It begins with a focused V1 implementation and will evolve as new business requirements, scale requirements, integration requirements, and operational challenges are introduced.

The goal is not only to build a working application, but also to understand the engineering decisions behind production systems: APIs, databases, transactions, concurrency, integrations, event-driven systems, testing, observability, containerization, deployment, data pipelines, failure recovery, and system design.

---

## Problem Statement

NovaCart receives customer orders from multiple sales channels such as:

- E-commerce websites
- Customer-support systems
- Offline/physical stores
- Future external sales channels

Without a centralized order-processing platform, different channels could implement inventory checks, payment processing, cancellations, fulfillment, and status tracking differently.

NovaCart provides a common order-processing workflow so that orders from every supported channel follow consistent business rules.

Conceptually:


Website ───────────────┐
                       │
Customer Support ──────┼──────► NovaCart
                       │
Physical Store ────────┘
                              │
                              ▼
                       Order Processing
                              │
                 ┌────────────┼────────────┐
                 ▼            ▼            ▼
             Inventory     Payments    Fulfillment


---

# Users

NovaCart may be used directly or indirectly by:

- Customers
- Customer Support
- Warehouse Staff
- Inventory Teams
- Delivery/Fulfillment Teams
- Operations Teams
- Analytics and Reporting Teams
- Management
- External Sales Channels

Different users require different views of the same underlying order lifecycle.

For example:


Customer
→ Where is my order?

Warehouse
→ What needs to be packed?

Customer Support
→ What happened to this order?

Inventory Team
→ How much stock is available?

Analytics
→ How many orders were fulfilled?

Operations
→ Which orders are stuck?


---

# Project Evolution

NovaCart is intentionally being developed incrementally.


V1
Core Order & Fulfillment Platform
        │
        ▼
Future Versions
Additional business capabilities
        │
        ▼
Distributed Systems
Events, asynchronous processing and integrations
        │
        ▼
Production Engineering
Observability, resiliency, scaling and deployment
        │
        ▼
Data Platform
Analytics, pipelines and operational reporting


Each major architectural addition should solve an identified business or technical problem rather than being introduced solely for technological complexity.

Git history and project documentation will preserve how the system evolves over time.

---

# Current Version — V1

## V1 Goal

Build a reliable core order-processing system capable of:

1. Receiving orders from multiple external channels.
2. Validating order requests.
3. Checking inventory availability.
4. Selecting an eligible warehouse.
5. Reserving inventory without overselling.
6. Processing payment.
7. Confirming successful orders.
8. Sending confirmed orders into fulfillment.
9. Tracking the fulfillment lifecycle.
10. Supporting eligible cancellations.
11. Releasing inventory when required.
12. Tracking refunds.
13. Preventing duplicate business operations.
14. Maintaining order history.
15. Providing operational and reporting data.

---

# V1 Order Lifecycle

The primary successful order lifecycle is:


PENDING
   │
   ▼
PAYMENT_PENDING
   │
   ▼
CONFIRMED
   │
   ▼
PACKING
   │
   ▼
READY_FOR_SHIPMENT
   │
   ▼
SHIPPED
   │
   ▼
OUT_FOR_DELIVERY
   │
   ▼
DELIVERED


Cancellation introduces an alternative terminal state when permitted:


PENDING ───────────────► CANCELLED

PAYMENT_PENDING ───────► CANCELLED

CONFIRMED ─────────────► CANCELLED

PACKING ───────────────► CANCELLED

READY_FOR_SHIPMENT ────► CANCELLED


Normal V1 cancellation is not allowed after the order reaches `SHIPPED`.

---

# V1 High-Level Order Flow


Order Request
      │
      ▼
Validate Request
      │
      ▼
Check Inventory
      │
      ▼
Find Eligible Warehouse
      │
      ├──── No warehouse can fulfill order
      │                 │
      │                 ▼
      │            Reject Order
      │
      ▼
Reserve Inventory
      │
      ▼
Process Payment
      │
      ├──── Payment Failed
      │           │
      │           ▼
      │    Release Reservation
      │
      ▼
Payment Successful
      │
      ▼
CONFIRMED
      │
      ▼
Warehouse Fulfillment
      │
      ▼
PACKING
      │
      ▼
READY_FOR_SHIPMENT
      │
      ▼
SHIPPED
      │
      ▼
OUT_FOR_DELIVERY
      │
      ▼
DELIVERED


---

# V1 Functional Requirements

### Order Intake

**FR-001:** The system must be able to receive orders from multiple external sales channels.

**FR-002:** The system must verify that sufficient inventory is available for every item in an order before accepting the order.

**FR-003:** The system must reserve the required inventory for an order before payment is processed.

### Payments

**FR-004:** The system must process payment only after inventory has been successfully reserved.

**FR-005:** The system must release reserved inventory if payment for an order fails.

**FR-006:** The system must mark an order as `CONFIRMED` after payment succeeds.

### Fulfillment

**FR-007:** The system must make confirmed orders available for warehouse fulfillment.

**FR-008:** The system must track orders throughout the fulfillment lifecycle.

### Cancellation and Refunds

**FR-009:** The system must support cancellation of eligible orders.

**FR-010:** When a valid cancellation occurs, the system must release inventory associated with the cancelled order and make eligible stock available again.

**FR-011:** When a paid order is successfully cancelled, the system must request a refund through the payment provider.

**FR-012:** The system must track refund status independently from order status.

**FR-013:** The system must prevent repeated cancellation requests from releasing inventory, initiating refunds, or performing other cancellation effects more than once.

### Idempotency

**FR-014:** The system must support idempotent order creation so retrying the same order-creation request does not create duplicate orders or reserve inventory multiple times.

### Operations and Reporting

**FR-015:** The system must expose sufficiently fresh order and fulfillment information to operational users.

**FR-016:** The system must make order and inventory information available for reporting and analytics.

### Order History

**FR-017:** The system must maintain the current status of an order.

**FR-018:** The system must maintain a historical record of order status transitions.

### Shipping Address

**FR-019:** The system must preserve the shipping address associated with an order independently of changes to the customer's current address.

**FR-020:** The system must support changing an order's shipping address only during eligible stages of the order lifecycle.

---

# V1 Business Rules

**BR-001:** An order may be cancelled only before it reaches `SHIPPED`.

**BR-002:** An order may proceed only when sufficient inventory is available for every item in the order.

**BR-003:** V1 uses an all-or-nothing inventory policy. If any item has insufficient inventory, inventory must not be reserved for only part of the order.

**BR-004:** Inventory must never be oversold.

**BR-005:** Payment must not be processed until inventory for all order items has been successfully reserved.

**BR-006:** If payment fails after inventory has been reserved, the reservation must be released.

**BR-007:** An order becomes `CONFIRMED` only after the required inventory has been reserved and payment has succeeded.

**BR-008:** Only confirmed orders may proceed to warehouse fulfillment.

**BR-009:** A valid cancellation of a paid order must initiate the refund process.

**BR-010:** Cancelling an order must release its inventory only once.

**BR-011:** Repeating the same business request must not cause the corresponding business operation to execute multiple times.

**BR-012:** A repeated order-creation request with the same idempotency key represents the same business operation and must not create another order.

**BR-013:** A new order-creation request with a different idempotency key represents a separate business operation even when customer, products, and quantities are identical.

**BR-014:** Normal order cancellation is not permitted once the order reaches `SHIPPED`.

**BR-015:** Fraud detection is outside the scope of V1.

**BR-016:** A single V1 order must be fulfilled entirely from one warehouse.

**BR-017:** A warehouse is eligible to fulfill an order only when it has sufficient available inventory for every order item.

**BR-018:** Warehouse selection must use available inventory rather than total inventory.

**BR-019:** When concurrent orders compete for limited inventory, inventory must be allocated only to orders that successfully reserve it. Inventory must never be oversold.

**BR-020:** The shipping address may be changed only while an order is `PENDING` or `PAYMENT_PENDING`. Once the order reaches `CONFIRMED`, its shipping address is locked.

---

# Inventory Model

Inventory is tracked by product and warehouse.

Conceptually:


Product
   │
   ├──── Bangalore Warehouse
   │        total = 10
   │        reserved = 3
   │        available = 7
   │
   └──── Mumbai Warehouse
            total = 20
            reserved = 5
            available = 15


For V1:


available_quantity =
    total_quantity - reserved_quantity


Important inventory invariants include:


total_quantity >= 0

reserved_quantity >= 0

reserved_quantity <= total_quantity


The combination:


(product_id, warehouse_id)


must uniquely identify an inventory record.

---

# Warehouse Selection

V1 does not support split fulfillment.

If an order contains:


Product A × 2
Product B × 3


one warehouse must have sufficient available inventory for **both products**.

This is not allowed in V1:


Product A → Bangalore
Product B → Mumbai


The entire order must be fulfilled from a single eligible warehouse.

Warehouse-selection rules will evolve as the project introduces additional fulfillment requirements.

---

# Concurrency

NovaCart must handle multiple customers attempting to purchase the same limited inventory concurrently.

Example:


Available stock = 1

Customer A ───► reserve
Customer B ───► reserve


The system must guarantee:


At most one reservation succeeds.


The implementation must prevent:


available = -1


or multiple successful reservations against the same physical stock.

Concurrency handling will be implemented and tested explicitly during development.

---

# Idempotency

Distributed systems can retry requests.

Example:


Website
   │
   ├──── Create Order ────► NovaCart
   │
   │                       Order created
   │
   │      response lost
   │◄────────── X
   │
   └──── Retry ───────────► NovaCart


Without idempotency, NovaCart could accidentally create two orders.

V1 therefore requires order-creation requests to include an idempotency key controlled by the calling system.


Same idempotency key
        ↓
Same business operation


Retries must not create duplicate orders or duplicate inventory reservations.

---

# Refund Rules

Refunds are modeled independently from payments and orders.

A payment may have multiple refund transactions.

Conceptually:


Payment = ₹10,000

Refund 1 = ₹6,000
Remaining refundable balance = ₹4,000


A subsequent refund request for ₹5,000 must not be accepted because it exceeds the remaining refundable amount.

Pending/in-progress refund operations must also be considered when determining whether another refund can be initiated.

Failed refund operations must release the corresponding refundable balance for future refund attempts.

---

# Order History

NovaCart stores both:


Order.status


and historical status transitions.

`Order.status` answers:

> Where is the order now?

Order status history answers:

> What happened to the order over time?

Example:


10:00  PENDING
10:05  PAYMENT_PENDING
10:07  CONFIRMED
10:30  PACKING
12:15  READY_FOR_SHIPMENT
14:47  SHIPPED


Status-history records may capture:

- Order identifier
- Status
- Transition timestamp
- Actor responsible for the transition
- Reason/context

---

# Core Domain Model

The initial domain contains:


Customer
Order
OrderItem
Product
Inventory
Warehouse
Payment
Refund
Fulfillment
OrderStatusHistory


High-level relationships:


Customer
   │
   └────< Orders
             │
             ├────< OrderItems >──── Product
             │                         │
             │                         └────< Inventory >──── Warehouse
             │
             ├────< Payments
             │         │
             │         └────< Refunds
             │
             ├──── Fulfillment ─────── Warehouse
             │
             └────< OrderStatusHistory


V1 relationship assumptions include:


One Customer
    → many Orders

One Order
    → many OrderItems

One Product
    → many OrderItems

One Product
    → many Inventory records

One Warehouse
    → many Inventory records

One Order
    → many Payment attempts

One Payment
    → many Refunds

One Order
    → one Fulfillment in V1

One Order
    → many OrderStatusHistory records


---

# Initial Application Architecture

NovaCart begins as a modular backend application rather than prematurely splitting the system into microservices.


External Client
      │
      ▼
    HTTP API
      │
      ▼
   API Layer
      │
      ▼
 Service Layer
 Business Logic
      │
      ▼
 Database Layer
      │
      ▼
   PostgreSQL


Additional infrastructure will be introduced when requirements justify it.

---

# Technology Stack

The initial implementation is expected to use:

### Application

- Python
- FastAPI
- Pydantic
- Uvicorn

### Database

- PostgreSQL

### Database Integration

The project will initially explore direct Python/PostgreSQL interaction so the underlying SQL and database behavior remain visible.

An abstraction/ORM such as SQLAlchemy may be introduced after the underlying database interactions are understood.

### Testing

- pytest
- API integration tests
- Database integration tests
- Concurrency tests
- Failure-path tests

### Infrastructure

Docker and additional deployment tooling will be introduced as the system evolves.

---

# Repository Structure

The repository will evolve with the application.

Initial target structure:


ecommerce-fulfillment/
│
├── app/
│   ├── __init__.py
│   ├── main.py
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes/
│   │
│   ├── schemas/
│   │
│   ├── services/
│   │
│   └── db/
│
├── tests/
│
├── docs/
│   ├── requirements/
│   ├── architecture/
│   └── adr/
│
├── .gitignore
├── requirements.txt
└── README.md


Responsibilities:


app/api/
    HTTP/API endpoints

app/schemas/
    API request and response contracts

app/services/
    Business workflows and rules

app/db/
    Database connectivity and persistence

tests/
    Automated tests

docs/requirements/
    Version-specific requirements

docs/architecture/
    Architecture documentation and diagrams

docs/adr/
    Architecture Decision Records


The structure will grow only when additional responsibilities justify new components.

---

# Documentation Strategy

The root README describes NovaCart as an overall platform.

Detailed version-specific requirements will be maintained separately:


docs/requirements/v1.md
docs/requirements/v2.md
...


Architecture decisions that materially affect the system will be documented using Architecture Decision Records (ADRs).

Examples may include:


Why PostgreSQL was selected

Why V1 uses single-warehouse fulfillment

How inventory concurrency is controlled

Why an event-driven workflow was introduced

Why a cache was introduced

Why a service was separated from the original application


This preserves not only **what** NovaCart looks like, but **why it evolved that way**.

---

# Non-Functional Requirements

Detailed measurable targets will evolve as stakeholder requirements become clearer.

Areas NovaCart must eventually address include:

### Correctness

The system must protect critical business invariants such as inventory consistency, payment/refund consistency, and idempotency.

### Reliability

Failures must not leave orders, payments, inventory, or fulfillment records in silently inconsistent states.

### Concurrency

Concurrent order processing must not result in overselling.

### Security

Credentials and secrets must not be stored directly in source code.

Applications should follow least-privilege access principles.

### Observability

The production system should provide sufficient logging, metrics, tracing, and operational visibility to diagnose failures.

### Performance

Operational workflows should receive sufficiently fresh information for their business needs.

### Auditability

Important order, payment, refund, inventory, and fulfillment changes should be traceable.

### Maintainability

Application responsibilities should remain sufficiently separated so that the system can evolve without concentrating all logic in API handlers or individual modules.

---

# Out of Scope for V1

The following capabilities are intentionally excluded from the initial implementation unless requirements change:

- Split fulfillment across multiple warehouses
- Post-shipment returns
- Fraud detection
- Advanced warehouse optimization
- Advanced shipping-carrier optimization
- Recommendation systems
- Dynamic pricing
- International tax engines
- Multi-region deployment
- Complex promotion engines

These may become future requirements.

---

# Future Evolution

Potential future phases may introduce requirements around:

### Order Management

- Partial cancellations
- Returns
- Exchanges
- Backorders
- Pre-orders

### Inventory

- Multi-warehouse split fulfillment
- Reservation expiration
- Stock replenishment
- Inventory movements
- Safety stock
- Warehouse transfers

### Payments

- Multiple payment methods
- Partial payments
- Payment retries
- Payment-provider failover
- Partial refunds
- Payment reconciliation

### Fulfillment

- Multiple shipments per order
- Carrier integrations
- Shipment tracking
- Delivery exceptions
- Reverse logistics

### Distributed Systems

- Asynchronous processing
- Message queues/event streaming
- Event-driven workflows
- Outbox patterns
- Retry mechanisms
- Dead-letter handling
- Distributed idempotency

### Performance

- Caching
- Database indexing
- Query optimization
- Connection pooling
- Horizontal scaling

### Reliability

- Circuit breakers
- Timeouts
- Retry policies
- Graceful degradation
- Disaster recovery

### Observability

- Structured logging
- Metrics
- Distributed tracing
- Dashboards
- Alerting
- SLOs and SLIs

### Data Engineering

- Operational event pipelines
- Analytics datasets
- ETL/ELT pipelines
- Data quality checks
- Reporting models
- Warehousing
- Batch and streaming processing

### Infrastructure

- Docker
- CI/CD
- Cloud deployment
- Kubernetes where justified
- Infrastructure as Code
- Secrets management

The actual architecture will evolve from demonstrated requirements rather than adopting all of these technologies by default.

---

# Engineering Principles

NovaCart development follows several principles:

### Understand the business before designing the system

Technical decisions should trace back to business requirements and constraints.

### Protect invariants

Critical rules such as preventing overselling should not depend solely on optimistic assumptions about callers.

### Do not trust external input blindly

Values controlled by NovaCart, such as authoritative product pricing and order status, should be determined by the appropriate system rather than blindly accepted from clients.

### Design for retries and failures

Networks, databases, payment providers, and downstream systems can fail. Failure behavior is part of the design.

### Prefer explicit business operations

Operations such as cancellation involve business workflows rather than merely changing a database field.

### Keep historical truth

Current state and historical state serve different purposes and should be modeled appropriately.

### Avoid premature complexity

Microservices, event streaming, caches, orchestration platforms, and other infrastructure should be introduced to solve demonstrated problems.

### Learn by troubleshooting

The project intentionally includes failure scenarios, concurrency problems, malformed requests, database failures, integration failures, and operational debugging.

---

# Learning Objectives

By evolving NovaCart, this project aims to develop practical understanding of:

- Requirements discovery
- Stakeholder questioning
- Domain modeling
- API design
- HTTP
- Python backend engineering
- FastAPI
- Data validation
- PostgreSQL
- SQL and relational modeling
- Transactions
- Isolation and locking
- Concurrency
- Idempotency
- Payment workflows
- Distributed systems
- Event-driven architecture
- Data engineering
- Testing
- Docker
- CI/CD
- Cloud infrastructure
- Observability
- Reliability engineering
- Production debugging
- Architecture trade-offs
- Customer-facing technical communication

The objective is not simply to know individual technologies, but to understand how they work together to solve real customer and operational problems.

---

# Project Status

**Current stage:** V1 — Core Order & Fulfillment Platform

The project is under active development.

The first implementation milestone is to establish the core application structure and progressively implement:


API
 ↓
Order validation
 ↓
Database persistence
 ↓
Inventory
 ↓
Warehouse selection
 ↓
Reservation
 ↓
Payment
 ↓
Confirmation
 ↓
Fulfillment
 ↓
Cancellation / Refunds


Each capability will be implemented, tested, deliberately stressed, and refined before introducing unnecessary additional infrastructure.