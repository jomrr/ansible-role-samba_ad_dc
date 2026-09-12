# Ansible Role: samba_ad_dc

![GitHub](https://img.shields.io/github/license/jomrr/ansible-role-samba_ad_dc)
![GitHub last commit](https://img.shields.io/github/last-commit/jomrr/ansible-role-samba_ad_dc)
![GitHub issues](https://img.shields.io/github/issues-raw/jomrr/ansible-role-samba_ad_dc)
[![dev](https://img.shields.io/github/actions/workflow/status/jomrr/ansible-role-samba_ad_dc/dev.yml?branch=dev&event=push&label=dev)](https://github.com/jomrr/ansible-role-samba_ad_dc/actions/workflows/dev.yml?query=branch%3Adev)
[![main](https://img.shields.io/github/actions/workflow/status/jomrr/ansible-role-samba_ad_dc/main.yml?branch=main&event=push&label=main)](https://github.com/jomrr/ansible-role-samba_ad_dc/actions/workflows/main.yml?query=branch%3Amain)

Ansible role for provisioning, joining, and running Samba Active Directory
domain controllers.

## Scope

### Managed

- Samba AD DC packages and native Python bindings.
- Tranquil IT Samba 4.24 repository, verified signing key, EPEL, and CRB on
  AlmaLinux 10 x86_64.
- Validated smb.conf with SYSVOL and NETLOGON shares.
- SMB signing, strong LDAP authentication, optional TLS, and authentication,
  directory, and share auditing.
- New AD forest provisioning with jomrr.samba.samba_provision, internal DNS, and
  the generated Kerberos configuration.
- Additional writable DC joins with jomrr.samba.samba_join_dc and internal DNS.
- Optional Windows LAPS schema preparation on the schema FSMO owner.
- Disabling standalone SMB, NetBIOS and winbind services, and enabling the
  integrated AD DC service.
- Domain password settings and fine-grained password policies.

### Not Managed

- Domain migration, demotion, or password rotation.
- SYSVOL synchronization.
- LAPS OU permissions, password reader/reset delegation, and Windows client
  Group Policy.
- BIND DNS backends.
- AD users, groups, OUs, and DNS records; managed by samba_ad_objects.

## Requirements

- A dedicated host without an existing Samba domain or custom Samba
  configuration.
- Samba AD DC packages and native bindings for the Python interpreter used by
  Ansible.
- A stable, non-loopback IP address and an FQDN matching samba_ad_dc_hostname
  and samba_ad_dc_realm.
- Available DNS port 53; check for conflicting listeners such as
  systemd-resolved or another DNS server.
- For joins, working AD DNS and Kerberos discovery, synchronized time, and
  connectivity to the existing DC.

## Dependencies

```yaml
collections:
  - name: community.crypto
    version: '>=3.0.0'
  - name: community.general
    version: '>=12.0.0'
  - name: jomrr.samba
    version: '>=1.0.1'
```

## Role Variables

### `samba_ad_dc_mode`

Type: `str`. Required: `false`.

Create a new domain or join an existing domain as an additional writable DC.

Default:

```yaml
samba_ad_dc_mode: provision
```

### `samba_ad_dc_join_server`

Type: `str`. Required: `false`.

Existing DC DNS hostname; required in join mode and unused in provision mode.

### `samba_ad_dc_join_site`

Type: `str`. Required: `false`.

Existing AD site for the new DC; omitted lets Samba select the site during the
join.

### `samba_ad_dc_realm`

Type: `str`. Required: `true`.

Kerberos realm and DNS domain to provision or join; immutable after
initialization.

### `samba_ad_dc_domain`

Type: `str`. Required: `true`.

NetBIOS domain name; immutable after provisioning.

### `samba_ad_dc_admin_password`

Type: `str`. Required: `true`.

Administrator password for provisioning, joining, and password policies,
supplied through a secret store.

### `samba_ad_dc_hostname`

Type: `str`. Required: `false`.

Short DNS hostname of the DC; must match the host identity and is immutable
after provisioning.

Default:

```yaml
samba_ad_dc_hostname: '{{ ansible_facts.hostname }}'
```

### `samba_ad_dc_function_level`

Type: `str`. Required: `false`.

DC functional level; initial provisioning also sets the domain and forest levels
to this value.

Default:

```yaml
samba_ad_dc_function_level: '2016'
```

### `samba_ad_dc_use_rfc2307`

Type: `bool`. Required: `false`.

Enable RFC2307 POSIX attributes at provision time and their use by the DC.

Default:

```yaml
samba_ad_dc_use_rfc2307: true
```

### `samba_ad_dc_laps`

Type: `bool`. Required: `false`.

Prepare the Windows LAPS schema; OU permissions and client policies are
configured separately. Disabling preserves existing schema extensions.

Default:

```yaml
samba_ad_dc_laps: false
```

### `samba_ad_dc_dns_forwarders`

Type: `list`. Required: `false`.

Upstream DNS server addresses; an empty list disables external DNS forwarding.

Default:

```yaml
samba_ad_dc_dns_forwarders: []
```

### `samba_ad_dc_rpc_dynamic_port_range`

Type: `str`. Required: `false`.

Dynamic RPC server port range; firewall rules must match.

Default:

```yaml
samba_ad_dc_rpc_dynamic_port_range: 49152-65535
```

### `samba_ad_dc_kdc_supported_enctypes`

Type: `list`. Required: `false`.

Encryption types accepted by the KDC; defaults exclude RC4.

Default:

```yaml
samba_ad_dc_kdc_supported_enctypes:
  - aes128-cts-hmac-sha1-96
  - aes256-cts-hmac-sha1-96
```

### `samba_ad_dc_kdc_default_domain_supported_enctypes`

Type: `list`. Required: `false`.

Encryption types for accounts without an explicit encryption-type value.

Default:

```yaml
samba_ad_dc_kdc_default_domain_supported_enctypes:
  - aes128-cts-hmac-sha1-96
  - aes256-cts-hmac-sha1-96
```

### `samba_ad_dc_restrict_anonymous`

Type: `int`. Required: `false`.

Restriction of anonymous SAMR and IPC access; 2 denies anonymous IPC
connections.

Default:

```yaml
samba_ad_dc_restrict_anonymous: 2
```

### `samba_ad_dc_server_min_protocol`

Type: `str`. Required: `false`.

Minimum accepted SMB dialect; SMB3 is Samba's alias for SMB3_11 and rejects
older dialects.

Default:

```yaml
samba_ad_dc_server_min_protocol: SMB3
```

### `samba_ad_dc_server_signing`

Type: `str`. Required: `false`.

SMB signing policy; mandatory requires integrity protection.

Default:

```yaml
samba_ad_dc_server_signing: mandatory
```

### `samba_ad_dc_ntlm_auth`

Type: `str`. Required: `false`.

Accept NTLMv2 fallback or require Kerberos; NTLMv1 is unsupported.

Default:

```yaml
samba_ad_dc_ntlm_auth: ntlmv2-only
```

### `samba_ad_dc_ldap_require_strong_auth`

Type: `str`. Required: `false`.

LDAP protection policy; simple binds require TLS and plain SASL requires signing
or sealing.

Default:

```yaml
samba_ad_dc_ldap_require_strong_auth: 'yes'
```

### `samba_ad_dc_password_hash_schemes`

Type: `list`. Required: `false`.

Additional userPassword hashes for external LDAP synchronization; disabled by
default.

Default:

```yaml
samba_ad_dc_password_hash_schemes: []
```

### `samba_ad_dc_tls_enabled`

Type: `bool`. Required: `false`.

Enable LDAPS and StartTLS; disabling TLS preserves the LDAP strong
authentication policy.

Default:

```yaml
samba_ad_dc_tls_enabled: true
```

### `samba_ad_dc_tls_keyfile`

Type: `path`. Required: `false`.

PEM private key on the DC, absolute or relative to Samba's private directory;
default is generated by Samba.

Default:

```yaml
samba_ad_dc_tls_keyfile: tls/key.pem
```

### `samba_ad_dc_tls_certfile`

Type: `path`. Required: `false`.

PEM server certificate and intermediate chain on the DC; default is generated by
Samba.

Default:

```yaml
samba_ad_dc_tls_certfile: tls/cert.pem
```

### `samba_ad_dc_tls_cafile`

Type: `path`. Required: `false`.

PEM CA bundle on the DC; default is generated by Samba.

Default:

```yaml
samba_ad_dc_tls_cafile: tls/ca.pem
```

### `samba_ad_dc_tls_crlfile`

Type: `str`. Required: `false`.

Optional existing PEM revocation list on the DC; empty leaves it unconfigured.

Default:

```yaml
samba_ad_dc_tls_crlfile: ''
```

### `samba_ad_dc_tls_dh_params_file`

Type: `str`. Required: `false`.

Optional existing DH parameter file on the DC; empty uses GnuTLS defaults.

Default:

```yaml
samba_ad_dc_tls_dh_params_file: ''
```

### `samba_ad_dc_tls_priority`

Type: `str`. Required: `false`.

GnuTLS cipher policy; defaults to TLS 1.2 and 1.3 with at least 128-bit cipher
security.

Default:

```yaml
samba_ad_dc_tls_priority: SECURE128:-VERS-ALL:+VERS-TLS1.3:+VERS-TLS1.2
```

### `samba_ad_dc_log_level`

Type: `str`. Required: `false`.

Samba audit classes and destinations, including authentication, directory
changes, and SYSVOL writes.

Default:

```yaml
samba_ad_dc_log_level: 1 auth_json_audit:5@/var/log/samba/auth_json_audit.log dsdb_json_audit:5@/var/log/samba/dsdb_json_audit.log
  dsdb_password_json_audit:5@/var/log/samba/dsdb_password_json_audit.log dsdb_group_json_audit:5@/var/log/samba/dsdb_group_json_audit.log
  dsdb_transaction_json_audit:10@/var/log/samba/dsdb_transaction_json_audit.log
  kerberos:3@/var/log/samba/kerberos.log drs_repl:2@/var/log/samba/drs_repl.log
  full_audit:1@/var/log/samba/sysvol_audit.log dns:2@/var/log/samba/dns.log
```

### `samba_ad_dc_max_log_size`

Type: `int`. Required: `false`.

Maximum size in KiB per Samba log before rotation to one .old file; 0 disables
the limit.

Default:

```yaml
samba_ad_dc_max_log_size: 10000
```

### `samba_ad_dc_audit_success`

Type: `list`. Required: `false`.

Successful VFS operations to audit; all includes reads, ACL changes, and newly
supported operations.

Default:

```yaml
samba_ad_dc_audit_success:
  - all
```

### `samba_ad_dc_audit_failure`

Type: `list`. Required: `false`.

Failed VFS operations to audit; all includes denied reads, ACL changes, and
metadata access.

Default:

```yaml
samba_ad_dc_audit_failure:
  - all
```

### `samba_ad_dc_audit_log_secdesc`

Type: `bool`. Required: `false`.

Record the requested Windows security descriptor in SDDL when clients change
ACLs.

Default:

```yaml
samba_ad_dc_audit_log_secdesc: true
```

### `samba_ad_dc_password_policy`

Type: `dict`. Required: `false`.

Domain password and lockout settings; unspecified values remain unchanged.

Default:

```yaml
samba_ad_dc_password_policy: {}
```

### `samba_ad_dc_password_settings`

Type: `list`. Required: `false`.

Fine-grained password policies; item settings override the configured domain
password settings.

Default:

```yaml
samba_ad_dc_password_settings: []
```

## Managed Files

- `/etc/yum.repos.d/tissamba.repo` Signed Samba 4.24 AD DC packages for
  AlmaLinux 10 x86_64.
- `/etc/pki/rpm-gpg/RPM-GPG-KEY-TISSAMBA-10` Package signing key for the
  AlmaLinux repository.
- `/etc/samba/smb.conf` Complete configuration; validated with testparm and
  backed up before replacement.
- `/etc/krb5.conf` Provisioned Kerberos configuration; the existing file is
  backed up.
- `/var/lib/samba` Domain databases, secrets, and SYSVOL.
- `/var/log/samba` Root-only Samba logs, including authentication and SYSVOL
  audits.

## Check Mode

Check mode is supported after provisioning or joining, including LAPS schema
changes on the schema FSMO owner. A clean host cannot complete a dry run because
packages, the AD database, and krb5.conf do not yet exist.

## Service Behavior

Changes to smb.conf or the LAPS schema restart the AD DC service.

## Security Notes

- LAPS password attributes use the confidential, never-value-audit, and
  RODC-filtered flags (searchFlags 904); expiration time remains readable
  without password read permission. The role grants no domain-wide SELF or
  password reader permissions.
- Disable Windows LAPS password encryption: this Samba setup stores passwords as
  confidential JSON in AD. Encrypted backups, DSRM management, and rollback
  detection are unsupported. Configure Windows client password rotation through
  Group Policy as shown below.
- Defaults deny anonymous IPC access, require SMB signatures, and reject NTLMv1.
  samba_ad_dc_server_min_protocol uses SMB3, Samba's alias for SMB3_11,
  rejecting SMB 2.x, 3.0, and 3.0.2. Select an explicit dialect when older
  clients are required. NetBIOS, including the integrated nbt service, and
  printing are disabled.
- LDAP simple binds require TLS; SASL on port 389 requires signing or sealing.
  TLS is enabled by default. With `samba_ad_dc_tls_enabled: false`, simple binds
  are unavailable and SASL still requires signing or sealing.
- Without custom TLS paths, Samba creates self-signed certificates in
  /var/lib/samba/private/tls on first startup. For trusted TLS, provide
  CA-issued certificates with the DC FQDN in subjectAltName and distribute CA
  trust to clients.
- Custom TLS files must exist on the DC: a matching unencrypted PEM RSA key
  (samba_ad_dc_tls_keyfile), server certificate with intermediate chain
  (samba_ad_dc_tls_certfile), and CA bundle (samba_ad_dc_tls_cafile). Keep the
  key root-owned with mode 0600 in a protected directory. Paths may be absolute
  or relative to Samba's private directory.
- Replacing a certificate at the same path requires a DC restart. Changing a TLS
  path through the role triggers that restart.
- TLS 1.2 and 1.3 use GnuTLS SECURE128 for compatibility with RSA certificates
  and 128-bit cipher suites.
- CRLs and DH parameter files are optional and must already exist on the DC. DH
  parameters map to Samba's `tls dh params file`.
- The KDC accepts AES128 and AES256 by default, including for accounts without
  an explicit encryption-type value. Existing service accounts and keytabs must
  contain AES keys.
- Extra userPassword hashes are disabled to avoid storing additional
  password-derived secrets. Enable CryptSHA256 or CryptSHA512 only for external
  LDAP integrations that require them.
- JSON level 5 records authentication and authorization failures and successes,
  Kerberos service access, anonymous sessions, and directory, group, and
  password changes. Transaction level 10 records commits, rollbacks, and commit
  failures; correlate transaction IDs to identify committed directory changes.
- DNS level 2 records update requests and refused unsigned updates in
  /var/log/samba/dns.log. DRS level 2 records completed GetNCChanges cycles and
  secret-replication decisions in /var/log/samba/drs_repl.log, with limited
  request context.
- SYSVOL and NETLOGON audit successful and failed VFS operations: connections,
  reads, writes, truncation, server-side copies, deletion, ACL/owner and
  metadata changes, links, and DFS modifications. The `all` selector includes
  new operations such as rename_stream and avoids removed names such as
  audit_file on Samba 4.24. Full audit precedes dfs_samba4 and acl_xattr to
  record the requested Windows ACL and final result, with SDDL enabled.
- Share audits use Samba's file logger at /var/log/samba/sysvol_audit.log. The
  prefix records IP, user, dialect, and share. SMB connections on port 445 do
  not supply a NetBIOS machine name.
- Samba rotates debug and JSON audit logs at samba_ad_dc_max_log_size KiB to one
  .old file. Anonymous sessions and full VFS auditing include every read and
  filesystem probe, increasing log volume and I/O. Restrict
  samba_ad_dc_audit_success and samba_ad_dc_audit_failure to reduce volume;
  operation names must match the installed Samba version.
- MIT Kerberos builds log ticket issuance and failures to
  /var/log/samba/mit_kdc.log through the provisioned kdc.conf. Samba's max log
  size does not apply to this file.
- LDAP searches/reads and individual DNS queries are not audited.

## Operational Notes

- samba_ad_dc_mode defaults to provision for a new forest. Set it to join on a
  new additional DC and supply samba_ad_dc_join_server as the existing DC's
  FQDN. samba_ad_dc_join_site optionally selects an existing AD site. Both modes
  use Administrator and samba_ad_dc_admin_password. The join uses Kerberos
  authentication; DNS and Kerberos client prerequisites must work before the
  role runs. A repeat join is an idempotent no-op; joining an already
  initialized DC to another realm is refused.
- Provision the first DC before running join mode on additional hosts. Configure
  the joiner's resolver to use an existing AD DNS server before the join; a
  resolver pointing only to itself cannot discover the domain before its DNS
  service exists. The role installs the generated Kerberos configuration after
  initialization. Domain and forest function levels are inherited during a join;
  samba_ad_dc_function_level configures the local DC level and, for new forests,
  the domain and forest levels. samba_ad_dc_use_rfc2307 also controls the local
  idmap setting, so it must match the existing domain's use of POSIX attributes.
- Enable samba_ad_dc_laps on the schema FSMO owner to create or reconcile the
  seven `msLAPS-*` attributes, the encrypted-password property set, and
  computer-class membership using native Samba bindings. Schema updates are
  enabled only for that connection. Legacy `ms-Mcs-*` LAPS is not configured.
- LAPS schema extensions are permanent and replicate forest-wide; back up the
  domain before enabling them. Disabling samba_ad_dc_laps stops schema
  management and preserves attributes, passwords, OU permissions, and client
  policies. msLAPS-CurrentPasswordVersion does not enable Windows Server 2025
  features.
- Realm, NetBIOS domain, and hostname identify the initialized DC and must not
  change afterwards. Provisioning settings do not migrate an existing domain or
  raise its functional level.
- Align firewall rules with samba_ad_dc_rpc_dynamic_port_range when narrowing
  the dynamic RPC range.
- Configure samba_ad_dc_dns_forwarders for external DNS names and avoid
  forwarding loops. Loopback forwarders require a separate local resolver on the
  specified port.
- AlmaLinux 10 x86_64 uses Tranquil IT's tis-samba 4.24 repository for AD DC
  packages and native Python bindings. EPEL supplies python3-setproctitle; CRB
  supplies additional dependencies. The signing key is checked by SHA-256
  checksum and OpenPGP fingerprint; package signature and HTTPS verification are
  enabled. Other Enterprise Linux versions and architectures are unsupported; an
  AlmaLinux image tagged latest must still use major version 10.
- molecule test -s dev tests all five container platforms as first-DC and
  joined-DC pairs, including idempotency, check mode, Kerberos, and replication
  in both directions. The vm scenario covers SELinux on first DCs.
- VM tests require x86_64, KVM, libvirt access, Vagrant, and vagrant-libvirt. In
  ansible-factory, install the tooling with `uv sync --locked --group vagrant`
  and use .ansible/venv/bin. The fixtures use the official Fedora 44 libvirt
  image with a pinned checksum and the official almalinux/10 Vagrant box, each
  with 2 GiB RAM and two vCPUs. Vagrant needs a directory-backed pool for qcow2
  overlays; set SAMBA_AD_DC_VM_STORAGE_POOL when the default pool uses LVM.
- VM tests cover DNS, Kerberos, SMB, TLS, audits, SELinux Enforcing, file
  contexts, and Samba access denials, plus TLS and LAPS opt outs for first DCs.
  Join integration is covered by the container pairs. The rootless UID
  workaround applies only to containers.
- samba_ad_dc_password_policy manages only the specified domain settings. PSO
  item settings override those configured values; other fields are copied from
  the domain when a PSO is created and retained on subsequent runs. applies_to
  is the exact set of assigned users or global security groups. Use state:
  absent to delete a PSO; removing it from the list stops management. Check the
  effective policy with `samba-tool domain passwordsettings pso show-user
  <username>`.
- PSO assignments require existing users or global security groups. Create
  custom accounts with samba_ad_objects before assigning their password
  policies.

## Supported Platforms

| OS Family | Distribution | Version | Container Image |
| --------- | ------------ | ------- | --------------- |
| RedHat | AlmaLinux | latest | [jomrr/molecule-almalinux:latest](https://hub.docker.com/r/jomrr/molecule-almalinux) |
| Debian | Debian | latest | [jomrr/molecule-debian:latest](https://hub.docker.com/r/jomrr/molecule-debian) |
| RedHat | Fedora | latest | [jomrr/molecule-fedora:latest](https://hub.docker.com/r/jomrr/molecule-fedora) |
| Suse | OpenSuse Tumbleweed | latest | [jomrr/molecule-opensuse-tumbleweed:latest](https://hub.docker.com/r/jomrr/molecule-opensuse-tumbleweed) |
| Debian | Ubuntu | latest | [jomrr/molecule-ubuntu:latest](https://hub.docker.com/r/jomrr/molecule-ubuntu) |

## Example Playbook

### Provision a new domain

```yaml
---

- name: SAMBA_AD_DC | Provision the first domain controller
  hosts: dc1
  gather_facts: true
  roles:
    - role: jomrr.samba_ad_dc
      samba_ad_dc_realm: AD.EXAMPLE.COM
      samba_ad_dc_domain: EXAMPLE
      samba_ad_dc_admin_password: "{{ vault_samba_ad_dc_admin_password }}"
      samba_ad_dc_dns_forwarders:
        - 192.0.2.53

```

### Join an additional writable domain controller

The existing DC must already serve the domain. DNS, Kerberos discovery,
and time synchronization on dc2 must work before this play runs.

```yaml
---

- name: SAMBA_AD_DC | Join the existing domain
  hosts: dc2
  gather_facts: true
  roles:
    - role: jomrr.samba_ad_dc
      samba_ad_dc_mode: join
      samba_ad_dc_join_server: dc1.ad.example.com
      samba_ad_dc_join_site: Default-First-Site-Name
      samba_ad_dc_hostname: dc2
      samba_ad_dc_realm: AD.EXAMPLE.COM
      samba_ad_dc_domain: EXAMPLE
      samba_ad_dc_admin_password: "{{ vault_samba_ad_dc_admin_password }}"
      samba_ad_dc_laps: false

```

### Narrow the dynamic RPC range

```yaml
samba_ad_dc_rpc_dynamic_port_range: 50000-55000
```

### Use existing PKI certificates

```yaml
samba_ad_dc_tls_keyfile: /etc/samba/tls/dc1.key
samba_ad_dc_tls_certfile: /etc/samba/tls/dc1.crt
samba_ad_dc_tls_cafile: /etc/samba/tls/ca.crt
```

### Disable TLS

```yaml
samba_ad_dc_tls_enabled: false
```

### Prepare Windows LAPS

After enabling schema preparation, delegate permissions per workstation OU
from Windows with the LAPS PowerShell module:

```powershell
Import-Module LAPS
$ou = "OU=Workstations,DC=ad,DC=example,DC=com"
Set-LapsADComputerSelfPermission -Identity $ou
Set-LapsADReadPasswordPermission -Identity $ou `
  -AllowedPrincipals "EXAMPLE\LAPS-Readers"
Set-LapsADResetPasswordPermission -Identity $ou `
  -AllowedPrincipals "EXAMPLE\LAPS-Resetters"
Find-LapsADExtendedRights -Identity $ou
```

Use approved groups and review inherited extended rights. Link a Windows
LAPS GPO to the OU with Active Directory as the backup directory and password
encryption disabled. Configure password settings and the local account,
apply `gpupdate /force`, and verify retrieval with
`Get-LapsADPassword -Identity <computer>` as an authorized reader.

```yaml
samba_ad_dc_laps: true
```

### Set domain and administrator password rules

```yaml
samba_ad_dc_password_policy:
  minimum_length: 12
  history_length: 24
  complexity: true
  reversible_encryption: false
samba_ad_dc_password_settings:
  - name: domain_admins
    precedence: 10
    applies_to: [Domain Admins]
    settings:
      minimum_length: 16
```

## References

- [Tranquil IT: Configure Windows LAPS for Samba AD](https://samba.tranquil.it/doc/en/samba_advanced_methods-samba_configure_laps.html)
- [Microsoft: Windows LAPS schema reference](https://learn.microsoft.com/en-us/windows-server/identity/laps/laps-technical-reference)
- [jomrr.samba collection](https://github.com/jomrr/ansible-collection-samba)
- [Samba testparm manual](https://www.samba.org/samba/docs/current/man-html/testparm.1.html)
- [Tranquil IT: Samba AD security tips](https://samba.tranquil.it/doc/en/samba_advanced_methods-samba_active_directory_higher_security_tips.html)
- [Samba smb.conf manual](https://www.samba.org/samba/docs/current/man-html/smb.conf.5.html)
- [Samba full audit manual](https://www.samba.org/samba/docs/current/man-html/vfs_full_audit.8.html)
- [GnuTLS priority strings](https://gnutls.org/manual/html_node/Priority-Strings.html)
- [Tranquil IT: Samba AD on RHEL and derivatives](https://samba.tranquil.it/doc/en/samba_config_server-server_install_samba_redhat.html)
- [Tranquil IT: Samba AD password policies](https://samba.tranquil.it/doc/en/samba_advanced_methods-samba_password_policies.html)

## Author

[Jonas Mauer](https://github.com/jomrr)

## License

This project is licensed under the MIT License.
See [LICENSE](LICENSE) for the full license text.

Copyright (c) 2026 Jonas Mauer.
