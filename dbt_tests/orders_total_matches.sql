select
    order_id,
    subtotal_amount,
    tax_amount,
    handling_amount,
    discount_amount,
    total_amount,

    GREATEST(
        {{ order_total(
            'subtotal_amount',
            'tax_amount',
            'handling_amount',
            'discount_amount'
        ) }},
        0
    ) as calculated_total

from {{ ref('fct_orders') }}

where abs(
    total_amount
    -
    (
        GREATEST(
            {{ order_total(
                'subtotal_amount',
                'tax_amount',
                'handling_amount',
                'discount_amount'
            ) }},
            0
        )
    )
) > 0.01