select
    order_id,
    customer_id,
    warehouse_id,
    status,
    subtotal_amount,
    tax_amount,
    handling_amount,
    discount_amount,
    total_amount,
    created_at,
    updated_at

from {{ ref('stg_orders') }}