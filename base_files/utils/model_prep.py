from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder


def split_data(TrainData,
               LabelData,
               TestSize: float = 0.2,
               RandomState: int = 1337):

    # Encoding labels for gradient boosters
    LabelEnc = LabelEncoder()
    TrainData = TrainData.to_numpy()
    LabelData = LabelEnc.fit_transform(LabelData)

    # Splitting the data
    (x_train,
     x_test,
     y_train,
     y_test) = train_test_split(TrainData,
                                LabelData,
                                test_size=TestSize,
                                random_state=RandomState)

    return x_train, x_test, y_train, y_test
