## `cloud-ipv4` Overview

This tool **automatically generates a MikroTik-ready IPv4 address-list** containing the public IP ranges for **AWS, GCP, and Azure**.

The file is updated automatically by a GitHub Action every **6 hours**.

-----

## MikroTik Import Instructions

To import the address list into your MikroTik router:

1.  **Fetch the script:**
    ```mikrotik
    /tool fetch url="https://raw.githubusercontent.com/andy72630/cloudIPv4/refs/heads/main/dist/all.rsc" dst-path=cloud.rsc
    ```
2.  **Import the list:**
    ```mikrotik
    /import file=cloud.rsc
    ```

-----

## How It Works

  * The core logic is in `scripts/generate.py`.
  * The script **fetches all cloud IPv4 prefixes**, **deduplicates** them, and then writes a **RouterOS script** (the `all.rsc` file).
  * The generated script is designed to **clear and repopulate** the address-list on your MikroTik device upon import.
  * A **GitHub Action** commits updates to `dist/all.rsc` only when the content of the file changes.

-----
