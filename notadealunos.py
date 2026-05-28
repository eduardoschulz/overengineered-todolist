nota1 = float(input('digite a nota 1: '))
nota2 = float(input('digite a nota 2: '))
nota3 = float(input('digite a nota 3: '))

media = (nota1+nota2+nota3)/3

if media >= 6:
    print('Aluno aprovado com media', media)

else:
    print('Aluno reprovado com média', media)