# Sample LookML View from Looker's default `sample_thelook_ecommerce` project
# Connection: sample_bigquery_connection (bigquery-public-data.thelook_ecommerce)

view: order_items {
  sql_table_name: `bigquery-public-data.thelook_ecommerce.order_items` ;;
  drill_fields: [id]

  dimension: id {
    primary_key: yes
    type: number
    sql: ${TABLE}.id ;;
  }

  dimension: order_id {
    type: number
    sql: ${TABLE}.order_id ;;
  }

  dimension: user_id {
    type: number
    sql: ${TABLE}.user_id ;;
  }

  dimension: inventory_item_id {
    type: number
    sql: ${TABLE}.inventory_item_id ;;
  }

  dimension: status {
    type: string
    description: "Order fulfillment status: Complete, Shipped, Processing, Cancelled, Returned"
    sql: ${TABLE}.status ;;
  }

  dimension: sale_price {
    type: number
    sql: ${TABLE}.sale_price ;;
  }

  # =========================================================================
  # GOVERNED SEMANTIC MEASURES (Looker Semantic Layer)
  # =========================================================================

  measure: total_gmv {
    label: "Gross Merchandise Value (GMV)"
    description: "Total retail value of all items sold before subtracting returns or cancellations. Excludes Cancelled orders."
    type: sum
    sql: ${sale_price} ;;
    filters: [status: "-Cancelled"]
    value_format_name: usd
  }

  measure: net_revenue {
    label: "Net Realized Revenue"
    description: "Actual realized revenue after excluding Cancelled and Returned items. SQL: SUM(order_items.sale_price) WHERE order_items.status NOT IN ('Cancelled', 'Returned')."
    type: sum
    sql: ${sale_price} ;;
    filters: [status: "-Cancelled, -Returned"]
    value_format_name: usd
  }

  measure: total_gross_margin {
    label: "Total Gross Margin ($)"
    description: "Total profit margin calculated as Net Realized Revenue minus inventory item cost. SQL: SUM(order_items.sale_price - inventory_items.cost) WHERE order_items.status NOT IN ('Cancelled', 'Returned'). Requires joining order_items.inventory_item_id = inventory_items.id."
    type: sum
    sql: ${sale_price} - ${inventory_items.cost} ;;
    filters: [status: "-Cancelled, -Returned"]
    value_format_name: usd
  }

  measure: return_rate {
    label: "Item Return Rate (%)"
    description: "Percentage of shipped/completed items that were returned. SQL: COUNTIF(order_items.status = 'Returned') / NULLIF(COUNTIF(order_items.status IN ('Complete', 'Shipped', 'Returned')), 0)."
    type: number
    sql: COUNTIF(${status} = 'Returned') / NULLIF(COUNTIF(${status} IN ('Complete', 'Shipped', 'Returned')), 0) ;;
    value_format_name: percent_2
  }
}
