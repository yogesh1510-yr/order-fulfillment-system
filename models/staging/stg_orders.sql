select
    order_id,
    customer_id,
    warehouse_id,
    idempotency_key,
    {{ normalize_status('status') }} as status,
    subtotal_amount,
    tax_amount,
    handling_amount,
    discount_amount,
    total_amount,
    created_at,
    updated_at

from {{ source('app', 'orders') }}