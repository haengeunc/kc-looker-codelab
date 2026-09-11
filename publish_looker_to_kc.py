#!/usr/bin/env python3
"""Publishes LookML semantic definitions from `sample_thelook_ecommerce` into Dataplex Knowledge Catalog.

Run directly in Google Cloud Shell:
    python3 publish_looker_to_kc.py --project haengeun-429200
"""

import argparse
import os
from google.api_core.exceptions import AlreadyExists
from google.cloud import dataplex_v1
from google.protobuf import struct_pb2

OVERVIEW_ASPECT_KEY = "655216118709.global.overview"
OVERVIEW_ASPECT_TYPE = "projects/dataplex-types/locations/global/aspectTypes/overview"


def publish_lookml_view_to_kc(project_id: str, location: str = "global") -> None:
  client = dataplex_v1.CatalogServiceClient()
  entry_group_id = "looker-semantic-layer"
  entry_type_id = "looker-view"
  parent = f"projects/{project_id}/locations/{location}"

  # 1. Ensure Entry Group exists
  entry_group_path = f"{parent}/entryGroups/{entry_group_id}"
  try:
    client.create_entry_group(
        parent=parent,
        entry_group_id=entry_group_id,
        entry_group=dataplex_v1.EntryGroup(
            display_name="Looker Semantic Layer (sample_thelook_ecommerce)",
            description="Governed LookML views, explores, and measures from sample_thelook_ecommerce",
        ),
    ).result()
    print(f"✅ Created Entry Group: {entry_group_path}")
  except AlreadyExists:
    print(f"✅ Entry Group already exists: {entry_group_path}")

  # 2. Ensure Entry Type `looker-view` exists
  entry_type_path = f"{parent}/entryTypes/{entry_type_id}"
  try:
    client.create_entry_type(
        parent=parent,
        entry_type_id=entry_type_id,
        entry_type=dataplex_v1.EntryType(
            display_name="Looker View",
            description="LookML View containing governed dimensions, measures, and SQL definitions",
        ),
    ).result()
    print(f"✅ Created Entry Type: {entry_type_path}")
  except AlreadyExists:
    print(f"✅ Entry Type already exists: {entry_type_path}")

  # 3. Read the LookML view file and build the Semantic Overview
  lookml_path = os.path.join(
      os.path.dirname(__file__),
      "sample_thelook_ecommerce",
      "order_items.view.lkml",
  )
  with open(lookml_path, "r", encoding="utf-8") as f:
    lookml_content = f.read()

  semantic_overview = f"""# Looker Semantic Layer: `sample_thelook_ecommerce.order_items`
- **Looker Project**: `sample_thelook_ecommerce`
- **Looker Connection**: `sample_bigquery_connection` (`bigquery-public-data.thelook_ecommerce`)
- **Explore**: `order_items` (joins `inventory_items` on `order_items.inventory_item_id = inventory_items.id` and `users` on `order_items.user_id = users.id`)

## Governed LookML Semantic Measures & SQL Formulas
1. **Gross Merchandise Value (`total_gmv`)**:
   - Definition: Total retail value of all items sold before subtracting returns, excluding Cancelled orders.
   - Governed SQL: `SUM(order_items.sale_price)` with filter `WHERE order_items.status != 'Cancelled'`
2. **Net Realized Revenue (`net_revenue`)**:
   - Definition: Actual realized revenue after excluding Cancelled and Returned items.
   - Governed SQL: `SUM(order_items.sale_price)` with filter `WHERE order_items.status NOT IN ('Cancelled', 'Returned')`
3. **Total Gross Margin (`total_gross_margin`)**:
   - Definition: Net Realized Revenue minus inventory item cost.
   - Governed SQL: `SUM(order_items.sale_price - inventory_items.cost)` with filter `WHERE order_items.status NOT IN ('Cancelled', 'Returned')` and join `JOIN bigquery-public-data.thelook_ecommerce.inventory_items ON order_items.inventory_item_id = inventory_items.id`
4. **Item Return Rate (`return_rate`)**:
   - Governed SQL: `COUNTIF(order_items.status = 'Returned') / NULLIF(COUNTIF(order_items.status IN ('Complete', 'Shipped', 'Returned')), 0)`

--- Raw LookML Definition ---
{lookml_content}
"""

  # 4. Upsert the Catalog Entry
  entry_id = "thelook-ecommerce-order-items-view"
  entry_path = f"{entry_group_path}/entries/{entry_id}"

  try:
    client.delete_entry(name=entry_path)
  except Exception:
    pass

  aspect_data = struct_pb2.Struct()
  aspect_data.update({"content": semantic_overview})

  entry = dataplex_v1.Entry(
      entry_type=entry_type_path,
      entry_source=dataplex_v1.EntrySource(
          resource="looker://sample_thelook_ecommerce/views/order_items",
          system="Looker",
          platform="Google Cloud",
          display_name="Looker View: order_items (sample_thelook_ecommerce)",
          description="Governed LookML semantic measures (Net Revenue, GMV, Gross Margin, Return Rate) for bigquery-public-data.thelook_ecommerce",
      ),
      aspects={
          OVERVIEW_ASPECT_KEY: dataplex_v1.Aspect(
              aspect_type=OVERVIEW_ASPECT_TYPE,
              data=aspect_data,
          )
      },
  )

  client.create_entry(
      parent=entry_group_path,
      entry_id=entry_id,
      entry=entry,
  )
  print(f"✅ Published LookML Semantic View to Knowledge Catalog: {entry_path}")


if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  parser.add_argument(
      "--project",
      default=os.environ.get("GOOGLE_CLOUD_PROJECT", "haengeun-429200"),
      help="GCP Project ID",
  )
  args = parser.parse_args()
  publish_lookml_view_to_kc(args.project)
