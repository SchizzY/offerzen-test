# Prompts

The prompts I gave the AI assistant (Claude, via Claude Code) while building this
project, in order and as typed (typos included). Long pasted terminal output is
trimmed, and replies to a specific part of an answer show the quoted part first.

See the [AI usage](README.md#ai-usage) section of the README for how the work was split.

## Session 1: environment and project setup (17–18 Nov 2026)

### 1

````text
Docker command to run docker <image> since I just have an image saved
````

### 2

````text
what if I want to search for a new one?
````

### 3

````text
how can I name the database?
````

### 4

````text
pgcli command to connect to the db
````

### 5

````text
➜  offerzen-test pgcli -h localhost -p 5432 -U admin -d offerzen-db
[pgcli traceback trimmed]
ImportError: dlopen(/opt/homebrew/Cellar/python@3.15/3.15.2/Frameworks/Python.framework/Versions/3.15/lib/python3.15/lib-dynload/pyexpat.cpython-315-darwin.so, 0x0002): Symbol not found: _XML_SetAllocTrackerActivationThreshold
➜  offerzen-test

pgcli has some issue
````

### 6

````text
expat 2.7.3 -> 2.10.0
==> Upgraded 1 dependent
poetry 2.1.1 -> 2.5.1_2
➜  offerzen-test pgcli -h localhost -p 5432 -U admin -d offerzen-db
[pgcli traceback trimmed]
ImportError: dlopen(/opt/homebrew/Cellar/python@3.15/3.15.2/Frameworks/Python.framework/Versions/3.15/lib/python3.15/lib-dynload/pyexpat.cpython-315-darwin.so, 0x0002): Symbol not found: _XML_SetAllocTrackerActivationThreshold
➜  offerzen-test

Updated some files but still same issues
````

### 7

````text
pyenv being used on this laptop?
````

### 8

````text
pipx isn't installed.
````

### 9

````text
[notice] A new release of pip is available: 24.3.1 -> 26.3
[notice] To update, run: ~/.venvs/pgcli/bin/python -m pip install --upgrade pip
Error: No such keg: /opt/homebrew/Cellar/pgcli
➜  offerzen-test

Okay please go ahead and fix pyenv, since I think we have a few python versions on this laptop not by pyenv.
````

### 10

````text
Let's just clean it up please. We can use pyenv to install the python versions needed.
````

### 11

````text
Nice, I want to initi poetry in a repo - how do I do this
````

### 12

````text
Installing the current project: offerzen-mrd-api (0.1.0)
Error: The current project could not be installed: Readme path `~/offerzen-test/README.md` does not exist.
If you do not want to install the current project use --no-root.
If you want to use Poetry only for dependency management but not for packaging, you can disable package mode by setting package-mode = false in your pyproject.toml file.
If you did intend to install the current project, you may need to set `packages` in your pyproject.toml file.

Been a while
````

### 13

````text
how can I find poetry packages
````

### 14

````text
open vsc in this dir for me please.
````

### 15

````text
Let's do the boiler plate for the entry file for fastapi please.
````

### 16

````text
we'll need to make a router please as well.
````

### 17

````text
we'll need a controller, then resource as well please.
````

### 18

````text
Okay keep it just slim please, so no tests yet please, just a single endpoint for the consumer
````

### 19

````text
Let's install alembic for the migrations and such we'll make
````

### 20

````text
[env.py](migrations/env.py) is a standard boiler plate. Would you have it copied or made via the CLI?
````

### 21

````text
Okay let's write a model 
product:
sku: varchar 100, name: varchar 255, price_cents: float, stock: int
````

### 22

````text
umm yeah run the autogenerate to have the file to be made, then write the SQL for the table.
````

### 23

````text
new model and migration
order
````

### 24

````text
orders
{order_ref: "web-100045", customer_id: "cust-42", items: [{sku: "BAN-001", qty: 2}, {sku: "APL-003", qty: 1}]}
````

### 25

````text
items seem to be jsonb field.
````

### 26

````text
Okay let's make the resources for basic crud
````

### 27

````text
I want you to generate a seeded db, you can include duplicates you know?
````

### 28

````text
vsc how do I seet the python interp for this venv?

[screenshot attached]
````

### 29

````text
okay check again
````

### 30

````text
I'd like to seed the products please.
````

### 31

````text
get pgcli to work please.
````

### 32

````text
I pulled valkey image in docker, I'd like to run it
````

### 33

````text
Nice, what are some good python valkey connectors?
````

### 34

````text
Let's build a module connector for valkey we can reuse in this system
````

### 35

````text
Go ahead and do the imports for valkey
````

### 36

````text
`asynccontextmanager` is depricated.
````

### 37

````text
Do a quick google.

[screenshot attached]
````

### 38

````text
remove the consumers router, controller and resource
````

### 39

````text
main, add orders endpoint. 

It's a create, we already have the schema/class so we have the type. Let's keep it type safe
````

### 40

````text
Before creating we need to check if an order already exists.
````

### 41

````text
Also we should hit the cache first, both for adding and checking.
````

### 42

````text
Make sure we're syncing both ways. In case the server crashes or valkey crashes we can roll back.
````

### 43

````text
we need a TTL that lives longer than the order, so we can make sure it's not growing forever. \
````

### 44

````text
Okay we'll also need to use the products resources here, as we'll need to adjust for the new orders. We can also take new orders even if stock is briefly. In case of order storms you know?
````

### 45

````text
Can we remove the comments please.
````

## Session 2: a side question (19 Nov 2026)

### 46

````text
when would I use SSE vs WS?
````

## Session 3: orders, stock, events, tests and README (18–20 Nov 2026)

### 47

````text
How do I read that?
```python
if not 0 < PENDING_TTL < ORDER_CACHE_TTL:
```
````

### 48

````text
we also need to calculate orders total, fairly straight forward please make a variable for this
````

### 49

````text
Make a status endpoint please, should be a single line return using the order id
````

### 50

````text
Pretty sure we should include a status when creating an order. 
```python
class OrderCreate(BaseModel):
    order_ref: str
    customer_id: str
    items: list[OrderItem] = []
```
````

### 51

````text
Well when someone makes an order do we not have it as a default of pending? We should update the migration so the defaults are correct.
````

### 52

````text
Let's turn our api on for the first time.
````

### 53

````text
write a curl command (I am lazy ngl) that I can do to create an order.
````

### 54

````text
Yeah, there was no response. Let's do a response please.
````

### 55

````text
Also these orders should be pending. Since there is nothing that updates them yet you know?
````

### 56

````text
curl for status on item 56
````

### 57

````text
we should also return a 200 and proper status codes please.
````

### 58

````text
Can we introduce openAPI as well for this please?
````

### 59

````text
can the examples include boiler plate already there please, also an endpoint to return orders, cursor based so we don't suffer from resources like a rolling window?
````

### 60

````text
Can we set this up

```
Includes a tiny script or command to seed a few products and submit a short burst of orders, intentionally including some duplicates
of the same order_ref.
```
````

### 61

````text
This seems correct
```
Seeded products: 0 inserted, the rest already existed
Firing 13 requests at once (6 distinct order_refs, run BURST-1795043048)

  201  BURST-1795043048-C     pending
  201  BURST-1795043048-E     pending
  409  BURST-1795043048-A     Order 'BURST-1795043048-A' already exists
  201  BURST-1795043048-D     pending
  201  BURST-1795043048-F     pending
  409  BURST-1795043048-C     Order 'BURST-1795043048-C' already exists
  409  BURST-1795043048-E     Order 'BURST-1795043048-E' already exists
  409  BURST-1795043048-A     Order 'BURST-1795043048-A' already exists
  201  BURST-1795043048-B     pending
  409  BURST-1795043048-C     Order 'BURST-1795043048-C' already exists
  201  BURST-1795043048-A     pending
  409  BURST-1795043048-C     Order 'BURST-1795043048-C' already exists
  409  BURST-1795043048-A     Order 'BURST-1795043048-A' already exists

Status codes: {201: 6, 409: 7}
  ok   BURST-1795043048-A     sent 4, created 1, 409 x3
  ok   BURST-1795043048-B     sent 1, created 1, 409 x0
  ok   BURST-1795043048-C     sent 4, created 1, 409 x3
  ok   BURST-1795043048-D     sent 1, created 1, 409 x0
  ok   BURST-1795043048-E     sent 2, created 1, 409 x1
  ok   BURST-1795043048-F     sent 1, created 1, 409 x0
  ok   stock deducted exactly once per created order
```
````

### 62

````text
Would you say we've completed.

Think even unhappy paths we've completed multiple.
```
Business constraints to guide your design (not implementation rules):
• An order might be submitted more than once with the same order_ref; only one should count.
• Orders should still be accepted during brief periods when the stock capability isn’t immediately reachable; stock should catch up
after recovery.
• Persist data in PostgreSQL. Don’t rely solely on in-memory state.
• Demonstrate exactly two representative unhappy paths:
1. duplicate submissions, and
2. a brief interruption/outage simulation with catch-up afterward.
Task 1: Orders intake
Design and implement an Orders capability that:
• Accepts a new order and stores it in PostgreSQL.
• Prevents the same order from being counted twice if it is submitted more than once with the same order_ref.

• Calculates an order total from product prices at the time of the order.
• Exposes a way to create an order and to fetch order details/status.
• Includes a tiny script or command to seed a few products and submit a short burst of orders, intentionally including some duplicates
of the same order_ref.
Keep this focused: no auth required; handle the two unhappy paths listed in the Requirements and keep any other edge
cases out of scope.
```
````

### 63

````text
Let's have a reset script please. So we can reset the environment for testing.
````

### 64

````text
This is our next endpoint
```
Endpoint to fetch order details/status⚠️ Partial. There's `/orders/{id}/status` and the list, but no `GET /orders/{id}` that returns the full order.
```
````

### 65

````text
**Order total from prices at the time of the order**❌ Missing. `order_total_cents` is calculated and then only logged, and that log level isn't even switched on. Nothing stores the total or the price paid per item, so a later price change can't be reconstructed.

Let's add the column, run the migration, update the schema and then let's make sure to calc on creation and store it please. Also return it with the other endpoints for order details.
````

### 66

````text
Update the seed as well.
````

### 67

````text
| Requirement | State |
| --- | --- |
| Store orders in PostgreSQL | ✅ Done |
| Same `order_ref` counted only once | ✅ Done. The burst script shows it under concurrent load, and the unique constraint in Postgres backs it up even if Valkey is wiped. |
| Seed and burst script with duplicates | ✅ Done |
| Endpoint to create an order | ✅ Done |
| Endpoint to fetch order details/status | ⚠️ Partial. There's `/orders/{id}/status` and the list, but no `GET /orders/{id}` that returns the full order. |
| **Order total from prices at the time of the order** | ❌ Missing. `order_total_cents` is calculated and then only logged, and that log level isn't even switched on. Nothing stores the total or the price paid per item, so a later price change can't be reconstructed. |
| **Accept orders while stock is unreachable, catch up after** | ❌ Missing. This is the big one. Stock is deducted inside the same transaction as the order, so if stock can't be reached, the order fails. Nothing gets queued and nothing catches up. |
| **Show the outage unhappy path** | ❌ Missing. Only the duplicate path is shown so far. |

Let's get an updated list please.
````

### 68

*Replying to this part of Claude's answer:*

> Valkey is a single point of failure. If it's down, creating an order returns 503, which contradicts "keep accepting orders during an outage". Postgres's unique constraint already prevents duplicates, so a Valkey outage should fall back to that check instead of failing.

````text
yeah db source of truth, we just do a valkey check first and write first but if it fails we should still check the db and write to the db. so we should check valkey and if it does not exist check the db to be sure. A sync process. How does that sound?
````

### 69

````text
Let's have valkey check the db first as mention to back fill so we're always in sync if valkey fails, same if db fails and valkey can write to the db once it's back up.
````

### 70

````text
where was those changes made
````

### 71

````text
cam we run the tests now for the paths using the seed and bursts?
````

### 72

````text
then give me an update on our list.
````

### 73

````text
Accept orders while stock is unreachable, catch up after

We should have this available but we'll have a catch up. Probably in part 2
````

### 74

````text
This is what is coming but not yet done. We'll work through it later

```
Task 2: Stock updates, catch-up, and external surface OR report
Design and implement stock handling that:
• Manages products and stock levels in PostgreSQL.
• Reduces stock when an order is accepted by the Orders capability.
• Demonstrates how stock catches up after a brief interruption (a simple pause/resume of a worker or component is sufficient).
• Exposes a way to read current stock for a SKU.
Then choose exactly one of the following to complete this task:
• Option A: Integration surface
• Provide a simple way for another system to consume “order accepted” information (your choice: feed, append-only log,
webhook, polling endpoint, etc.).
• Include a tiny consumer or script that shows how to receive/process these updates (printing to stdout is fine).
• Option B: Minimal report
• Provide a lightweight endpoint (your design) that returns for a given day:
• Total orders
• Revenue
• Units sold per SKU
• Current stock per SKU
• For this exercise, choosing this option satisfies the need for other teams to learn about accepted orders.
You decide how components communicate and how catch-up works. Keep the demonstration minimal but convincing.
```
````

### 75

````text
we should always make a created at and updated at as welll
````

### 76

````text
Can you explain task 2 to me plainly please?
````

### 77

````text
Let's talk right about what I did about task 1 and my weakpoints?
````

### 78

````text
Let's build a few .sh files to allow them to simulate runs, results in the terminal as well please. Let's set up a docker file as well. Latest progress image along with valkey
````

### 79

*Replying to this part of Claude's answer:*

> 2. The stock-outage constraint isn't met yet.
> "Orders should still be accepted when stock isn't reachable" is a Task 1 constraint. Leaving the catch-up for Task 2 makes sense, but right now intake still reduces stock inside the order transaction, so a stock failure fails the order. Separating the two is the first thing Task 2 should do.

````text
Let's brain storm a good way through this. I feel we don't reject the order but instead of removing the quantity we change it to 0 and charge them 0 for that item? Kafka what is the modern way of dealing with that?
````

### 80

````text
Well if someone for instance orders groceries, we can't back order that for them?
````

### 81

````text
yes please, this sounds good to me. This is how I was setting this up
````

### 82

````text
The docker container to be clear is only for postgres and valkey correct? Since we'll be using poetry to actually run the python server which they'd have cloned.
````

### 83

````text
➜  scripts sim-all.sh
zsh: command not found: sim-all.sh
➜  scripts bash sim-all.sh
✘ postgres isn't running. Start it with: ./scripts/up.sh
➜  scripts bash up.sh

━━━ Setting up ━━━

▶ Starting Postgres and Valkey
[+] up 3/5
 ✔ Network offerzen-test_default      Created                                                                                                      0.1s
 ✔ Volume offerzen-test_pgdata        Created                                                                                                      0.0s
 ✔ Volume offerzen-test_valkeydata    Created                                                                                                      0.0s
 ⠴ Container offerzen-test-valkey-1   Starting                                                                                                     0.6s
 ⠴ Container offerzen-test-postgres-1 Starting                                                                                                     0.6s
Error response from daemon: failed to set up container networking: driver failed programming external connectivity on endpoint offerzen-test-valkey-1 (5d9fd6c338c038a3811351c1d9e251c25ed82d11f446b35597342d4be8a07629): Bind for 0.0.0.0:6380 failed: port is already allocated
➜  scripts bash sim-all.sh
✘ postgres isn't running. Start it with: ./scripts/up.sh
➜  scripts

Not working as of yet, container detection is not great
````

### 84

````text
Explain task 2 to me again please, simply
````

### 85

*Replying to this part of Claude's answer:*

> Placing an order reduces stock, as a separate step.
> Right now the order and the stock deduction happen together, so if stock fails, the order fails.
> Instead, the order is saved immediately, and a background worker reduces stock a moment later.

````text
Let's start with this, we can at the controller level already use another thread we can spin up for this yeah?
````

### 86

````text
Okay let's make a table to understand what's done and what needs to be done both from step 1 and 2 please.
````

### 87

*Replying to this part of Claude's answer:*

> Read current stock for a SKU
> ❌ To do
> GET /products/{sku}/stock

````text
Nice, simple router endpoint, controller with  a get with url arg, resource as well please.
````

### 88

*Replying to this part of Claude's answer:*

> Show stock catching up after an interruption
> ⚠️ Partial
> The worker's pause, resume, status commands exist. Needs sim-stock-outage.sh with a PASS/FAIL.

````text
You'll need to explain more to me please when you can.
````

### 89

````text
yes please. then give me the tables again
````

### 90

*Replying to this part of Claude's answer:*

> Constraint: exactly two unhappy paths, keep focused

````text
Okay which paths do we currently have. In the ticket is it mentioned which paths we need to take?
````

### 91

````text
We should just do those two unhappy paths please.
````

### 92

````text
okay tables again
````

### 93

````text
what is A and what is B simply?
````

### 94

````text
A for sure, since I'd like to think cost for log storage isn't a concern right now.
````

### 95

````text
But don't just build it
````

### 96

````text
let's create a polling endpoint using websockets yeah? 

• Provide a simple way for another system to consume “order accepted” information (your choice: feed, append-only log,
webhook, polling endpoint, etc.).

Polling endpoint which we could also just make without a websocket
````

### 97

````text
include both, I think each time an order is created we stream it, let's build the endpoint. Let's do SSE actually for this.
````

### 98

````text
okay tables again please.
````

### 99

````text
Do a git init, create a private repo with the default branch being main
````

### 100

````text
remove crud functionality we're not using please
````

### 101

````text
Don't write a read me yet, commit an empty one, make a env demo as well please, with a command to make a real env for someone to fill in their details.
````

### 102

````text
As SchizzY right?
github account
````

### 103

````text
Fix this, this is when we're throwing 409's incorrectly at certain bad paths correct?
````

### 104

````text
changing `price_cents` to an integer. Yes make the migration please, currently I think it was made as a float.
````

### 105

````text
a few pytest tests

Build these.
````

### 106

````text
yes please. Then we can discuss the readme.

I want pre-req like needing docker, needing python, poetry you know
````

### 107

````text
small whys, a diagram, definitely disclose ai usage please. Windows will use WSL yeah
````

### 108

````text
okay table now please.
````

### 109

````text
you can commit and push please. also schizzy right is the github account?
````

### 110

````text
Okay can we also save the prompts I used here please in this chat?
````
