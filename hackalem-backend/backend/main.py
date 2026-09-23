from recommender.data_loader import load_contractors


contractors = load_contractors()

print("Количество подрядчиков:", len(contractors))

print("\nПервый подрядчик:")
print(contractors[0])
