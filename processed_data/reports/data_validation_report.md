# Data Validation & Preprocessing Report

**Generated:** 2026-09-06T07:17:41.606577+00:00

## 1. Dataset Row Counts & Integrity

| Dataset | Raw Rows | Processed Rows | Columns | Null Values Discovered & Retained |
| :--- | :--- | :--- | :--- | :--- |
| `customers` | 99,441 | 99,441 | 5 | None (0) |
| `orders` | 99,441 | 99,441 | 9 | order_delivered_carrier_date: 1,783, order_delivered_customer_date: 2,965, order_approved_at: 160 |
| `products` | 32,951 | 32,951 | 10 | product_name_lenght: 610, product_description_lenght: 610, product_photos_qty: 610, product_category_name: 610, product_category_name_english: 610, product_weight_g: 2, product_length_cm: 2, product_height_cm: 2, product_width_cm: 2 |
| `order_items` | 112,650 | 112,650 | 7 | None (0) |
| `order_payments` | 103,886 | 103,886 | 5 | None (0) |
| `bitext` | 26,872 | 26,872 | 5 | None (0) |

## 2. Customer Demo Personas

Total Demo Personas Created: **25**

| Demo ID | Display Name | Scenario | Total Orders | City / State | Sample Order ID |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `DEMO_00001` | **Customer 00001** | VIP_REPEAT_BUYER_17_ORDERS | 17 | sao paulo, SP | `c2213109a2cc0e75d55585b7aaac6d97` |
| `DEMO_00002` | **Customer 00002** | HIGH_VOLUME_REPEAT_BUYER_9_ORDERS | 9 | praia grande, SP | `826b47e4cd7bba4e4c6fa5485f898b74` |
| `DEMO_00003` | **Customer 00003** | REPEAT_BUYER_7_ORDERS | 7 | ituiutaba, MG | `43f08913407cac4e74a898d968e58c1a` |
| `DEMO_00004` | **Customer 00004** | REPEAT_BUYER_7_ORDERS | 7 | santos, SP | `72a704e8fb6c499fad9b26bd8873bd39` |
| `DEMO_00005` | **Customer 00005** | REPEAT_BUYER_7_ORDERS | 7 | recife, PE | `9e22fb4a47d29059ef9689ca8b26d8b3` |
| `DEMO_00006` | **Customer 00006** | IN_TRANSIT_SHIPPED_ORDER | 2 | jundiai, SP | `ee64d42b8cf066f35eac1cf57de1aa85` |
| `DEMO_00007` | **Customer 00007** | IN_TRANSIT_SHIPPED_ORDER | 1 | paracatu, MG | `6942b8da583c2f9957e990d028607019` |
| `DEMO_00008` | **Customer 00008** | CANCELED_ORDER_REFUND_INQUIRY | 1 | sao paulo, SP | `1b9ecfe83cdc259250e1a8aca174f0ad` |
| `DEMO_00009` | **Customer 00009** | CANCELED_ORDER_REFUND_INQUIRY | 2 | diadema, SP | `714fb133a6730ab81fa1d3c1b2007291` |
| `DEMO_00010` | **Customer 00010** | UNAVAILABLE_ORDER_ESCALATION | 1 | sao bento do sul, SC | `8e24261a7e58791d10cb1bf9da94df5c` |
| `DEMO_00011` | **Customer 00011** | DELIVERED_MULTI_ITEM_ORDER_5_ITEMS | 1 | pato branco, PR | `02a065131a2d2b72b45e2c63135606ad` |
| `DEMO_00012` | **Customer 00012** | SPLIT_PAYMENT_VOUCHER_AND_CREDIT | 1 | arapora, MG | `5cfd514482e22bc992e7693f0e3e8df7` |
| `DEMO_00013` | **Customer 00013** | DELIVERED_STANDARD_SP | 1 | santo andre, SP | `ad21c59c0840e6cb83a9ceb5573f8159` |
| `DEMO_00014` | **Customer 00014** | DELIVERED_STANDARD_RJ | 1 | nilopolis, RJ | `6514b8ad8028c9f2cc2374ded245783f` |
| `DEMO_00015` | **Customer 00015** | DELIVERED_STANDARD_MG | 1 | ouro preto, MG | `82566a660a982b15fb86e904c8d32918` |
| `DEMO_00016` | **Customer 00016** | DELIVERED_STANDARD_RS | 1 | faxinalzinho, RS | `76c6e866289321a7c93b82b54852dc33` |
| `DEMO_00017` | **Customer 00017** | DELIVERED_STANDARD_PR | 1 | congonhinhas, PR | `a4591c265e18cb1dcee52889e2d8acc3` |
| `DEMO_00018` | **Customer 00018** | DELIVERED_STANDARD_BA | 1 | barreiras, BA | `53cdb2fc8bc7dce0b6741e2150273451` |
| `DEMO_00019` | **Customer 00019** | DELIVERED_STANDARD_SC | 1 | imbituba, SC | `116f0b09343b49556bbad5f35bee0cdf` |
| `DEMO_00020` | **Customer 00020** | DELIVERED_STANDARD_DF | 1 | brasilia, DF | `948097deef559c742e7ce321e5e58919` |
| `DEMO_00021` | **Customer 00021** | DELIVERED_STANDARD_GO | 1 | vianopolis, GO | `47770eb9100c2d0c44946d9cf07ec65d` |
| `DEMO_00022` | **Customer 00022** | DELIVERED_STANDARD_PE | 1 | palmares, PE | `1790eea0b567cf50911c057cf20f90f9` |
| `DEMO_00023` | **Customer 00023** | DELIVERED_STANDARD_CE | 1 | ibiapina, CE | `60550084e6b4c0cb89a87df1f3e5ebd9` |
| `DEMO_00024` | **Customer 00024** | DELIVERED_STANDARD_ES | 1 | serra, ES | `74ebfa44a323c96a7760bd693d690a3d` |
| `DEMO_00025` | **Customer 00025** | DELIVERED_STANDARD_MT | 1 | cuiaba, MT | `a910f58086d58b3ae6f37aa712d377b9` |
