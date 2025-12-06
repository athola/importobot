# Key Rotation Guide

Rotating `IMPORTOBOT_ENCRYPTION_KEY` keeps encrypted credentials forward compatible with
policy updates or enterprise HSM requirements. Follow the steps below to rotate keys
safely.

1. **Install security extras** (cryptography + keyring support):
   ```bash
   pip install 'importobot[security]'
   ```

2. **Load the old key**. Export the current key one last time or configure access via
   the system keyring:
   ```bash
   export IMPORTOBOT_ENCRYPTION_KEY="$(cat /secure/location/current.key)"
   # or
   export IMPORTOBOT_KEYRING_SERVICE="importobot-ci"
   export IMPORTOBOT_KEYRING_USERNAME="automation"
   ```

3. **Generate a new key** and stage it in your HSM/keyring. You can keep using
   system tools, or let Importobot do the work:

   ```bash
   NEW_KEY=$(openssl rand -base64 32)
   security add-generic-password -a automation -s importobot-ci -w "$NEW_KEY"
   ```

   ```python
   from importobot.security import CredentialManager

   NEW_KEY = CredentialManager.store_key_in_keyring(
       service="importobot-ci",
       username="automation",
       overwrite=True,  # replace existing key when rotating
   )
   ```

4. **Rotate encrypted credentials** using the enterprise helper:
   ```python
   from importobot.security import CredentialManager
   from importobot_enterprise.key_rotation import rotate_credentials

   old = CredentialManager()
   new = CredentialManager(key=NEW_KEY)
   rotated = rotate_credentials(existing_encrypted_items, old, new)
   ```

5. **Deploy the new key**. Update `IMPORTOBOT_KEYRING_SERVICE` or the environment key
   on every host, then restart Importobot processes.

6. **Validate** using `CredentialManager.decrypt_credential` with the new key to ensure
   stored ciphertext decrypts correctly, and remove the old key from the keyring/HSM.

## Troubleshooting

- If rotation fails with `decryption failed`, verify the source manager still has
  access to the old key.
- For large credential inventories, process in batches and store the `RotationPlan`
  output to disk before replacing the old key.
- Always keep backups of ciphertexts until you confirm the new key works across all
  services consuming Importobot.
