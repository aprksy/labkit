# Incus Networking: Step-by-Step Summary (Your Lab)

## Lab Context
- Host IP: 10.0.1.1/16 (Alpine Linux)
- Private Incus network (NAT): incusbr0 → 10.1.0.0/16
- Goal:
  - Expose selected containers/VMs to the host network
  - Keep others hidden
  - Avoid port forwarding and SSH jump hosts

---

## Step 1 — Keep `incusbr0` as the Private Network
- Purpose: hidden, NATed instances
- No changes required

Hidden instance:
- NIC → `incusbr0`

---

## Step 2 — Create a Routed Incus Network (for exposure)

```bash
incus network create incus-routed \
  ipv4.address=10.1.0.1/16 \
  ipv4.nat=false \
  ipv6.address=none
````

* Provides L3 routing
* No NAT
* No port forwarding

---

## Step 3 — Enable IP Forwarding on the Host (Alpine)

```bash
sysctl -w net.ipv4.ip_forward=1
echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf
```

---

## Step 4 — Allow Forwarding Between Incus Networks

```bash
iptables -A FORWARD -i incusbr0 -o incus-routed -j ACCEPT
iptables -A FORWARD -i incus-routed -o incusbr0 -j ACCEPT
```

(No NAT rules needed.)

---

## Step 5 — Create Profiles (Recommended)

### Base Profile (no networking)

```bash
incus profile create base
```

### Private Network Profile

```bash
incus profile create net-private
```

```yaml
devices:
  eth0:
    type: nic
    network: incusbr0
```

### Routed Network Profile

```bash
incus profile create net-routed
```

```yaml
devices:
  eth0:
    type: nic
    network: incus-routed
```

---

## Step 6 — Launch Instances

### Hidden Instance

```bash
incus launch alpine:3.19 hidden1 -p base -p net-private
```

* Hidden from host/LAN
* Accessible only via NAT or from exposed nodes

---

### Exposed Instance

```bash
incus launch alpine:3.19 exposed1 -p base -p net-routed
```

* Directly reachable from host
* No port forwarding

---

### Dual-Homed Instance (Optional)

```bash
incus launch alpine:3.19 gw1 -p base -p net-private -p net-routed
```

Use only if the instance must route/firewall traffic.

---

## Step 7 — Optional: Expose Instances to the LAN

Add a route on your LAN gateway:

```
10.1.0.0/16 via 10.0.1.1
```

---

## Final Network Behavior

| Instance Type | Networks Attached | Reachable From Host | Reachable From LAN |
| ------------- | ----------------- | ------------------- | ------------------ |
| Hidden        | incusbr0          | ❌                   | ❌                  |
| Exposed       | incus-routed      | ✔                   | ❌ (default)        |
| Gateway       | Both              | ✔                   | ✔ (policy-based)   |

---

## Key Takeaways

* Exposure is controlled by **network attachment**, not port forwarding
* Hidden instances do **not** need dual NICs to be reachable from exposed ones
* Routing + firewalling on the host is the clean solution
* Profiles are templates, not isolation boundaries

