import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import ray
from PIL import Image
from tensorflow.keras.models import Model


pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', 10)

def show_weights(model: Model, name='model'):
    weights = []
    scattereds = []
    for i, w in enumerate(model.get_weights()):
        scattereds += [show_scattered_4d.remote(w, f'{name}[{i}]')]

    for i, w in enumerate(ray.get(scattereds)):
        IMG[f'{name}[{i}]'] = w
        weights.append(f'{name}[{i}]')

    return weights


def show_scattered(x, label="data"):
    print(f"#{label}=", x.shape)
    A = np.matrix(x)
    # scatter plot x - column 0, y - column 1, shown with marker o
    plt.plot(A[:, 0], A[:, 1], 'o', label=label)
    plt.legend()
    plt.show()


def show_scattered_3d(x3d, title="data"):
    print(f"#{title}=", x3d.shape)

    if (len(x3d.shape) == 2):
        x3d = x3d.reshape(x3d.shape[0], x3d.shape[1], 1)

    # Creating dataset
    z, x, y = x3d.nonzero()
    # c = [x3d[z[i]][x[i]][y[i]] for i in range(0, len(z))]
    print("x=", x)
    print("y=", y)
    print("z=", z)
    # print("c=", c)

    # Creating figure
    fig = plt.figure(figsize=(10, 7))
    ax = plt.axes(projection="3d")

    # Creating plot
    ax.scatter3D(x, y, z, color="green")
    # img = ax.scatter(x, y, z, c=c, cmap=plt.hot())
    # fig.colorbar(img)
    plt.title(title)

    # show plot
    plt.show()


@ray.remote
def show_scattered_4d(x3d, name="data"):
    title = f"{name}{x3d.shape}"

    if (len(x3d.shape) == 1):
        x3d = x3d.reshape(x3d.shape[0], 1, 1)
    elif (len(x3d.shape) == 2):
        x3d = x3d.reshape(x3d.shape[0], x3d.shape[1], 1)

    # Creating dataset
    # z,x,y = x3d.nonzero()
    # c = np.array([x3d[z[i]][x[i]][y[i]] for i in range(0, len(z))])

    z = []
    x = []
    y = []
    c = []
    for i in range(0, x3d.shape[0]):
        for j in range(0, x3d.shape[1]):
            for k in range(0, x3d.shape[2]):
                z.append(i)
                x.append(j)
                y.append(k)
                c.append(x3d[i][j][k])

    for i in [['c', c], ['x', x], ['y', y], ['z', z]]:
        i[1] = np.array(i[1])
        title = f"{title}\n{i[0]}[{i[1].min()} ... {i[1].mean()} ... {i[1].max()}]"

    # Creating figure
    fig = plt.figure(figsize=(10, 7))

    # plt.yticks(np.arange(min(y), max(y), 1))
    ax = plt.axes(projection="3d")
    # Creating plot
    img = ax.scatter(x, y, z, c=c, cmap=plt.cm.get_cmap('hot_r'), vmin=0, vmax=1)

    fig.colorbar(img)
    # plt.title(title)
    fig.suptitle(title, fontsize=13)
    fig.tight_layout()

    ## show plot
    # plt.show()
    # img_buf = io.BytesIO()
    # plt.savefig(img_buf, format='jpg')
    path = f"/cic/images/{name}.jpg"
    plt.savefig(path, bbox_inches='tight')
    plt.close(fig)
    return path


IMG = dict()


def show_4d_imgs(imgs, title=''):
    col = len(imgs)
    fig = plt.figure(figsize=(10 * col, 7))
    for i, x in enumerate(imgs):
        fig.add_subplot(1, col, i + 1)
        img = Image.open(IMG[x])
        plt.imshow(img)
        plt.axis('off')
    fig.tight_layout()
    plt.title(title)
    plt.show()


def show_train_metric(history, title="title"):
    plt.plot(history.history['loss'], label='Training loss')
    plt.plot(history.history['val_loss'], label='Validation loss')
    plt.title(title)
    plt.legend()
