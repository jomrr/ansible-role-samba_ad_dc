# Ansible Role: samba_dc

![GitHub](https://img.shields.io/github/license/jomrr/ansible-role-samba_dc) ![GitHub last commit](https://img.shields.io/github/last-commit/jomrr/ansible-role-samba_dc) ![GitHub issues](https://img.shields.io/github/issues-raw/jomrr/ansible-role-samba_dc) [![dev](https://img.shields.io/github/actions/workflow/status/jomrr/ansible-role-samba_dc/dev.yml?branch=dev&event=push&label=dev)](https://github.com/jomrr/ansible-role-samba_dc/actions/workflows/dev.yml?query=branch%3Adev) [![main](https://img.shields.io/github/actions/workflow/status/jomrr/ansible-role-samba_dc/main.yml?branch=main&event=push&label=main)](https://github.com/jomrr/ansible-role-samba_dc/actions/workflows/main.yml?query=branch%3Amain)

Ansible role for provisioning and running the first Samba Active Directory domain controller.

## Purpose

Establish the first domain controller of a new Active Directory forest using jomrr.samba.samba_provision and Samba's internal DNS backend.

## Scope

### Managed

- Samba AD DC packages and native Python bindings.
- Validated smb.conf with SYSVOL and NETLOGON shares.
- Secure protocol defaults, optional TLS, and authentication, directory, and share audit logging.
- Initial domain provisioning and installation of the generated Kerberos configuration.
- Disabling standalone SMB, NetBIOS and winbind services, and enabling the integrated AD DC service.

### Not Managed

- Joining additional DCs, domain migration, demotion, or password rotation.
- AD users, groups, OUs, and additional DNS objects.
- Hostname, IP addressing, resolver configuration, firewall rules, and time synchronization.
- BIND DNS backends and general-purpose file shares.
- External certificate issuance, deployment, renewal, and client trust distribution.
- Central audit collection, archival retention, and protection against privileged log tampering.

## Requirements

- Run with root privileges and gathered facts on a dedicated, unprovisioned host.
- Debian, Ubuntu, Fedora, or openSUSE Tumbleweed with the distribution's Samba AD DC packages.
- The system Python used by Ansible must load the distribution's Samba Python bindings.
- Configure a stable, non-loopback IP address and an FQDN matching samba_dc_hostname and samba_dc_realm.
- Ensure DNS port 53 is available, including any conflict with systemd-resolved or an existing DNS server.
- After provisioning, configure the DC and domain clients to resolve AD records through this DC.
- Allow Samba AD traffic through the firewall and provide working time synchronization for Kerberos.

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

The following variables are part of the public role interface.

| Name | Type | Required | Default | Description |
| ---- | ---- | -------- | ------- | ----------- |
| `samba_dc_realm` | `str` | `true` | | Kerberos realm and DNS domain of the new forest; immutable after provisioning. |
| `samba_dc_domain` | `str` | `true` | | NetBIOS domain name; immutable after provisioning. |
| `samba_dc_admin_password` | `str` | `true` | | Initial Administrator password supplied through Ansible Vault or a secret store. |
| `samba_dc_hostname` | `str` | `false` | `{{ ansible_facts.hostname }}` | Short DNS hostname of the DC; must match the host identity and is immutable after provisioning. |
| `samba_dc_function_level` | `str` | `false` | `2016` | Domain, forest, and DC functional level for initial provisioning; keep unchanged afterwards. |
| `samba_dc_use_rfc2307` | `bool` | `false` | `True` | Enable RFC2307 POSIX attributes at provision time and their use by the DC. |
| `samba_dc_dns_forwarders` | `list` | `false` | [] | Upstream DNS server addresses; an empty list disables external DNS forwarding. |
| `samba_dc_restrict_anonymous` | `int` | `false` | `2` | Restriction of anonymous SAMR and IPC access; 2 denies anonymous IPC connections. |
| `samba_dc_server_min_protocol` | `str` | `false` | `SMB3` | Minimum accepted SMB dialect; SMB3 is Samba's alias for SMB3_11 and rejects older dialects. |
| `samba_dc_server_signing` | `str` | `false` | `mandatory` | SMB signing policy; mandatory requires integrity protection. |
| `samba_dc_ntlm_auth` | `str` | `false` | `ntlmv2-only` | Accept NTLMv2 fallback or require Kerberos; NTLMv1 is unsupported. |
| `samba_dc_ldap_require_strong_auth` | `str` | `false` | `yes` | LDAP protection policy; simple binds require TLS and plain SASL requires signing or sealing. |
| `samba_dc_password_hash_schemes` | `list` | `false` | [] | Additional userPassword hashes for external LDAP synchronization; disabled by default. |
| `samba_dc_tls_enabled` | `bool` | `false` | `True` | Enable LDAPS and StartTLS; disabling TLS preserves the LDAP strong authentication policy. |
| `samba_dc_tls_keyfile` | `path` | `false` | `tls/key.pem` | PEM private key on the DC, absolute or relative to Samba's private directory; default is generated by Samba. |
| `samba_dc_tls_certfile` | `path` | `false` | `tls/cert.pem` | PEM server certificate and intermediate chain on the DC; default is generated by Samba. |
| `samba_dc_tls_cafile` | `path` | `false` | `tls/ca.pem` | PEM CA bundle on the DC; default is generated by Samba. |
| `samba_dc_tls_crlfile` | `str` | `false` | `` | Optional existing PEM revocation list on the DC; empty leaves it unconfigured. |
| `samba_dc_tls_dh_params_file` | `str` | `false` | `` | Optional existing DH parameter file on the DC; empty uses GnuTLS defaults. |
| `samba_dc_tls_priority` | `str` | `false` | `SECURE128:-VERS-ALL:+VERS-TLS1.3:+VERS-TLS1.2` | GnuTLS cipher policy; defaults to TLS 1.2 and 1.3 with at least 128-bit cipher security. |
| `samba_dc_log_level` | `str` | `false` | `1 auth_json_audit:5@/var/log/samba/auth_json_audit.log dsdb_json_audit:5@/var/log/samba/dsdb_json_audit.log dsdb_password_json_audit:5@/var/log/samba/dsdb_password_json_audit.log dsdb_group_json_audit:5@/var/log/samba/dsdb_group_json_audit.log dsdb_transaction_json_audit:10@/var/log/samba/dsdb_transaction_json_audit.log kerberos:3@/var/log/samba/kerberos.log drs_repl:2@/var/log/samba/drs_repl.log full_audit:1@/var/log/samba/sysvol_audit.log dns:2@/var/log/samba/dns.log` | Samba audit classes and destinations, including authentication, directory changes, and SYSVOL writes. |
| `samba_dc_max_log_size` | `int` | `false` | `10000` | Maximum size in KiB per Samba log before rotation to one .old file; 0 disables the limit. |
| `samba_dc_audit_success` | `list` | `false` | - all | Successful VFS operations to audit; all includes reads, ACL changes, and newly supported operations. |
| `samba_dc_audit_failure` | `list` | `false` | - all | Failed VFS operations to audit; all includes denied reads, ACL changes, and metadata access. |
| `samba_dc_audit_log_secdesc` | `bool` | `false` | `True` | Record the requested Windows security descriptor in SDDL when clients change ACLs. |

## Managed Files

- `/etc/samba/smb.conf` Complete configuration, validated with testparm before installation; previous content is backed up.
- `/etc/krb5.conf` Copied from Samba's provisioned configuration; previous content is backed up.
- `/var/lib/samba` Domain databases, secrets, and SYSVOL created by the collection module.
- `/var/log/samba` Root-only directory for Samba logs, including authentication and SYSVOL audit logs.

## Check Mode

Check mode is supported on an already provisioned host.

- A clean host cannot complete a dry run because packages, the database, and krb5.conf do not yet exist.

## Service Behavior

Configuration changes restart the integrated AD DC service after provisioning and Kerberos setup.

### Handlers

- restart domain controller

## Security Notes

- Supply samba_dc_admin_password through Ansible Vault or a secret store; provisioning is protected with no_log.
- The initial Administrator password is not rotated by subsequent runs.
- Defaults deny anonymous IPC access, require SMB 3.1.1 and SMB signatures, reject NTLMv1, and require TLS for LDAP simple binds or signing/sealing for SASL on port 389. NetBIOS (including the integrated nbt service) and printing are disabled.
- samba_dc_server_min_protocol defaults to SMB3, Samba's alias for SMB3_11. This is a minimum, not only a preference during negotiation: SMB 2.x, 3.0, and 3.0.2 clients are rejected by default. The existing explicit dialect choices remain available for deployments requiring older clients.
- TLS is enabled by default and can be disabled with samba_dc_tls_enabled: false. LDAP strong authentication remains enabled when TLS is disabled; simple password binds are then unavailable.
- All TLS paths are optional. Their defaults use Samba's generated self-signed certificates under /var/lib/samba/private/tls. These do not provide client trust automatically. For production, supply existing CA-issued certificates with the DC FQDN in the subjectAltName and configure client trust. Samba generates its default credentials on first startup; the role does not issue or renew external certificates.
- Custom TLS files must already exist on the DC. Supply a matching PEM RSA key, server certificate with intermediate chain, and CA bundle through samba_dc_tls_keyfile, samba_dc_tls_certfile, and samba_dc_tls_cafile. Keep the unencrypted private key root-owned with mode 0600 and its directory protected. Paths may be absolute or relative to Samba's private directory.
- After replacing certificate content at an unchanged path, the certificate deployment workflow must restart the DC service. Changing a TLS path through the role notifies its restart handler.
- The default GnuTLS priority SECURE128 permits TLS 1.2 and 1.3 only. This differs from Tranquil IT's SECURE256 profile to retain interoperability with common RSA certificates and 128-bit cipher suites. A stricter samba_dc_tls_priority can be selected for a compatible PKI and client fleet.
- CRLs and custom DH parameters remain optional existing files. The canonical Samba parameter is tls dh params file. CRL configuration does not replace certificate renewal or client revocation checking.
- Extra userPassword hashes are disabled by default. Tranquil IT describes CryptSHA256 and CryptSHA512 for password synchronization to external LDAP systems; enable them only for that integration.
- JSON authentication and authorization events use level 5, including failures, successful logons, Kerberos service access, and anonymous sessions. Directory, group, and password changes use level 5. Transaction auditing uses level 10 for commits as well as rollbacks and commit failures; correlate transaction identifiers before treating a directory change as persisted.
- DNS level 2 records update requests and refused unsigned updates in /var/log/samba/dns.log. The previous dns:0 setting omitted these refusals. DRS level 2 records replication diagnostics, including completed GetNCChanges cycles and secret-replication decisions, in /var/log/samba/drs_repl.log. These are diagnostic messages with limited request context, not Windows event 4662 or complete read auditing.
- SYSVOL and NETLOGON log all successful and failed VFS operations, including connections, reads, content changes, truncation, server-side copies, deletions, ACL/owner changes, metadata changes, links, and DFS modifications. The native all selector also covers new operations such as rename_stream without referencing removed operation names such as audit_file on Samba 4.24. Full audit runs before dfs_samba4 and acl_xattr to capture the requested Windows ACL and final result, with SDDL enabled by default.
- Share audit events go directly to /var/log/samba/sysvol_audit.log using Samba's file logger, so a separate syslog daemon and local7 routing are not required. The prefix includes IP, user, dialect, and share; the guide's NetBIOS machine field is unavailable with direct SMB on port 445.
- Samba rotates its debug and JSON audit logs at samba_dc_max_log_size KiB to one .old file. Anonymous sessions and full VFS auditing can generate substantial volume and I/O overhead, including every read and normal filesystem probes. Forward logs externally for durable retention and monitor rotation and disk usage. Explicit samba_dc_audit_success/failure lists can reduce volume when a narrower event policy is intended; their operation names must be supported by the installed Samba version.
- MIT Kerberos builds additionally write ticket issuance and failures to /var/log/samba/mit_kdc.log using Samba's provisioned kdc.conf; these native KDC logs need separate collection and rotation and are not covered by max log size. The MIT plugin does not emit the same JSON KDC events as Heimdal.
- This is service audit coverage, not a complete host audit. Local root access to the AD database or SYSVOL, smb.conf changes, service stops, firewall activity, and log tampering require host auditing and external monitoring. LDAP search/read auditing and individual DNS queries are not provided by the configured change-audit classes. DRS diagnostics do not replace DCSync detection and alerting. No Windows Security Event Log equivalence is implied.

## Operational Notes

- Realm, NetBIOS domain, hostname, function level, and RFC2307 provisioning choices describe the initial domain. Keep them unchanged after provisioning; the collection does not migrate or reconcile an existing domain.
- The role owns smb.conf and krb5.conf. It is intended for a new dedicated DC, not adoption of an existing Samba installation with custom paths or configuration.
- Configure samba_dc_dns_forwarders to resolve names outside the AD domain; avoid DNS forwarding loops. The guide's 127.0.0.1:5353 requires a separately configured resolver on that port and is not a universal default.
- Enterprise Linux distributions without Samba AD DC packages are not supported.

## Supported Platforms

| OS Family | Distribution | Version | Container Image |
| --------- | ------------ | ------- | --------------- |
| Debian | Debian | latest | [jomrr/molecule-debian:latest](https://hub.docker.com/r/jomrr/molecule-debian) |
| RedHat | Fedora | latest | [jomrr/molecule-fedora:latest](https://hub.docker.com/r/jomrr/molecule-fedora) |
| Suse | OpenSuse Tumbleweed | latest | [jomrr/molecule-opensuse-tumbleweed:latest](https://hub.docker.com/r/jomrr/molecule-opensuse-tumbleweed) |
| Debian | Ubuntu | latest | [jomrr/molecule-ubuntu:latest](https://hub.docker.com/r/jomrr/molecule-ubuntu) |

## Example Playbook

### Provision a new domain

Prepare host identity, networking, time synchronization, and DNS port availability before applying the role.

```yaml
---
- name: SAMBA_DC | Provision the first domain controller
  hosts: dc1
  become: true
  gather_facts: true
  roles:
    - role: jomrr.samba_dc
      samba_dc_realm: AD.EXAMPLE.COM
      samba_dc_domain: EXAMPLE
      samba_dc_admin_password: "{{ vault_samba_dc_admin_password }}"
      samba_dc_dns_forwarders:
        - 192.0.2.53

```

### Use existing PKI certificates

Deploy the certificate files beforehand and distribute CA trust to clients.

```yaml
samba_dc_tls_keyfile: /etc/samba/tls/dc1.key
samba_dc_tls_certfile: /etc/samba/tls/dc1.crt
samba_dc_tls_cafile: /etc/samba/tls/ca.crt
```

### Disable TLS

Use protected SASL authentication over LDAP; LDAPS and LDAP simple binds are unavailable.

```yaml
samba_dc_tls_enabled: false
```

## References

- [jomrr.samba collection](https://github.com/jomrr/ansible-collection-samba)
- [Samba testparm manual](https://www.samba.org/samba/docs/current/man-html/testparm.1.html)
- [Tranquil IT: Samba AD security tips](https://samba.tranquil.it/doc/en/samba_advanced_methods-samba_active_directory_higher_security_tips.html)
- [Samba smb.conf manual](https://www.samba.org/samba/docs/current/man-html/smb.conf.5.html)
- [Samba full audit manual](https://www.samba.org/samba/docs/current/man-html/vfs_full_audit.8.html)
- [GnuTLS priority strings](https://gnutls.org/manual/html_node/Priority-Strings.html)

## Author

[Jonas Mauer](https://github.com/jomrr)

## License

This project is licensed under the MIT License.
See [LICENSE](LICENSE) for the full license text.

Copyright (c) 2026 Jonas Mauer.
